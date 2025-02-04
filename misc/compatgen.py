#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re

CURL_GIT_PATH = os.environ.get("CURL_GIT_PATH", './curl')

target_dirs = [
    '{}/include/curl'.format(CURL_GIT_PATH),
    '/usr/local/include',
    'libdir/gcc/target/version/include'
    '/usr/target/include',
    '/usr/include',
]


def get_curl_path():
    for d in target_dirs:
        for root, dirs, files in os.walk(d):
            if 'curl.h' in files:
                return os.path.join(root, 'curl.h')
    raise Exception("Not found")


def version_symbol(ver):
    os.system('cd "{}" && git status --porcelain && git checkout -f "{}"'.format(CURL_GIT_PATH, ver))
    opts = []
    codes = []
    infos = []
    vers = []
    auths = []
    init_pattern = re.compile(r'CINIT\((.*?),\s*(LONG|OBJECTPOINT|FUNCTIONPOINT|STRINGPOINT|OFF_T),\s*(\d+)\)')
    error_pattern = re.compile('^\s+(CURLE_[A-Z_0-9]+),')
    info_pattern = re.compile('^\s+(CURLINFO_[A-Z_0-9]+)\s+=')
    with open(os.path.join(CURL_GIT_PATH, 'include', 'curl', 'curl.h')) as f:
        for line in f:
            match = init_pattern.findall(line)
            if match:
                opts.append("CURLOPT_" + match[0][0])
            if line.startswith('#define CURLOPT_'):
                o = line.split()
                opts.append(o[1])

            if line.startswith('#define CURLAUTH_'):
                a = line.split()
                auths.append(a[1])

            match = error_pattern.findall(line)
            if match:
                codes.append(match[0])

            if line.startswith('#define CURLE_'):
                c = line.split()
                codes.append(c[1])

            match = info_pattern.findall(line)
            if match:
                infos.append(match[0])

            if line.startswith('#define CURLINFO_'):
                i = line.split()
                if '0x' not in i[2]:  # :(
                    infos.append(i[1])

            if line.startswith('#define CURL_VERSION_'):
                i = line.split()
                vers.append(i[1])

    return opts, codes, infos, vers, auths


tags = os.popen("cd {} && git tag | grep -E '^curl-[7,8]_[0-9]+_[0-9]+$'".format(CURL_GIT_PATH)).read().split('\n')[:-1]
filtered_tags = filter(lambda t: ((int(t.split('-')[1].split('_')[0]) == 7) and (int(t.split('-')[1].split('_')[1]) >= 10)) or (int(t.split('-')[1].split('_')[0]) == 8), tags)
versions = sorted(filtered_tags, key=lambda o: (int(o.split('-')[1].split('_')[0]) * 10000 + int(o.split('-')[1].split('_')[1]) * 100 + int(o.split('-')[1].split('_')[2])), reverse=True)
last = version_symbol("master")

template = """
/* generated by compatgen.py */
#include<curl/curl.h>


"""

result = [template]
result_tail = ["/* generated ends */\n"]
if __name__ == '__main__':
    for ver in versions:
        print("the version is {}".format(ver))
        major = int(ver.split("_")[0].split('-')[1])
        minor, patch = map(int, ver.split("_")[-2:])

        opts, codes, infos, vers, auths = curr = version_symbol(ver)

        for o in last[0]:
            if o not in opts:
                result.append("#define {} 0".format(o))  # 0 for nil option
        for c in last[1]:
            if c not in codes:
                result.append("#define {} -1".format(c))  # -1 for error
        for i in last[2]:
            if i not in infos:
                result.append("#define {} 0".format(i))  # 0 for nil
        for v in last[3]:
            if v not in vers:
                result.append("#define {} 0".format(v))  # 0 for nil
        for a in last[4]:
            if a not in auths:
                result.append('#define {} 0'.format(a))  # 0 for nil

        result.append(
            "#if (LIBCURL_VERSION_MAJOR == {} && LIBCURL_VERSION_MINOR == {} && LIBCURL_VERSION_PATCH < {}) || (LIBCURL_VERSION_MAJOR == {} && LIBCURL_VERSION_MINOR < {}) ".format(
                major, minor, patch, major, minor))

        result_tail.insert(0, "#endif /* {}.{}.{} */".format(major, minor, patch))

        last = curr

result.append("#error your version is TOOOOOOOO low")

result.extend(result_tail)

with open("./compat.h", 'w') as fp:
    fp.write('\n'.join(result))
