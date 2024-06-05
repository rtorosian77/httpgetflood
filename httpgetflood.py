import subprocess
from multiprocessing import Pool
from contextlib import closing

poolSize = 2
attempts = 10
curlTimeout = 5
aggregate = {'http_code': {}, 'time_namelookup': float(0), 'time_connect': float(0), 'time_pretransfer': float(0), 'time_starttransfer': float(0), 'time_total': float(0), 'failure_rate': float(0)}

def execCurl():
    cmd = 'curl -k --max-time ' + str(curlTimeout) +  ' https://welcomeconnect.service-now.com/beneficiary  -s -o /dev/null -w "response_code: %{http_code} dns_time: %{time_namelookup} connect_time: %{time_connect} pretransfer_time: %{time_pretransfer} starttransfer_time: %{time_starttransfer} total_time: %{time_total}"'
    try:
        res = subprocess.check_output(cmd, shell=True)
        parts = res.split()
        return {'http_code': int(parts[1]), 'time_namelookup': float(parts[3]), 'time_connect': float(parts[5]), 'time_pretransfer': float(parts[7]), 'time_starttransfer': float(parts[9]), 'time_total': float(parts[11])}
    except:
        return False


def run(thread):
    failedAttempts = 0
    liveFailures = float(0)
    localAgg = {'http_code': {}, 'time_namelookup': float(0), 'time_connect': float(0), 'time_pretransfer': float(0), 'time_starttransfer': float(0), 'time_total': float(0)}
    for i in range(attempts):
        print("Thread " + str(thread) + ", attempt " + str(i+1))
        localRes = execCurl()
        if not localRes:
            failedAttempts += 1
            liveFailures += 1
            print('Curl failed in thread ' + str(thread) + ', attempt ' + str(i) + ', current failure rate: ' + str(round(liveFailures / attempts, 2)))
        else:
            for key,value in localRes.items():
                if 'http_code' in key:
                    if value in localAgg['http_code'].keys():
                        localAgg['http_code'][value] += 1
                    else:
                        localAgg['http_code'][value] = 1
                else:
                    localAgg[key] += value
    denom = attempts - failedAttempts
    if denom == 0:
        return False
    for key,value in localAgg.items():
        if key == 'http_code':
            pass
        else:
            localAgg[key] = round(value / denom, 2)
    localAgg['failure_rate'] = round(failedAttempts / attempts, 2)
    return localAgg

if __name__ == "__main__":
    with closing(Pool(processes=poolSize)) as pool:
        callbacks = pool.map_async(run, range(poolSize)).get(999999)
        for result in callbacks:
            if not result:
                print("No valid results from thread")
            else:
                for key,value in result.items():
                    if 'http_code' in key:
                        for hkey, hval in result['http_code'].items():
                            if hkey in aggregate['http_code'].keys():
                                aggregate['http_code'][hkey] += hval
                            else:
                                aggregate['http_code'][hkey] = hval
                        print('http_code counts:')
                        for hkey,hval in result['http_code'].items():
                            print('\t' + str(hkey) + ': ' + str(hval))
                    else:
                        aggregate[key] += value
                        print(key + ": " + str(value))
                print("**********************************")


    print("Average results:")
    for key,value in aggregate.items():
        if key == 'http_code':
            print('http_code counts:')
            for hkey,hval in aggregate['http_code'].items():
                print('\t' + str(hkey) + ': ' + str(hval))
        else:
            print(key + ": " + str(round(value / poolSize, 2)))
