#!/usr/bin/env python3
"""Exercise the actual vendor calloc C body with successful/failed allocation.

The host memset stub records a NULL destination instead of writing address zero.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uboot-tree', type=Path, required=True)
    args = parser.parse_args()
    source = (args.uboot_tree / 'common/malloc_simple.c').read_text()
    start = source.index('void *calloc(')
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    body = source[start:end].replace('void *calloc(', 'void *checked_calloc(', 1)
    preamble = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
static unsigned char buffer[128];
static int force_failure, alloc_calls, zero_calls, null_zero_calls;
static void reset(int fail) {
 force_failure=fail; alloc_calls=zero_calls=null_zero_calls=0;
 memset(buffer, 0xa5, sizeof(buffer));
}
static void *test_alloc(size_t size) {
 alloc_calls++;
 return force_failure || size > sizeof(buffer) ? NULL : buffer;
}
static void *test_zero(void *ptr, int value, size_t size) {
 zero_calls++;
 if (!ptr) { null_zero_calls++; return NULL; }
 assert(ptr == buffer && size <= sizeof(buffer));
 return memset(ptr, value, size);
}
#define malloc test_alloc
#define memset test_zero
'''
    harness = r'''
#undef malloc
#undef memset
int main(void) {
 assert(sizeof(size_t)==8);
 reset(0);
 void *normal = checked_calloc(4,8);
 int success = normal == buffer;
 for(int i=0;i<32;i++) success &= buffer[i]==0;
 success &= buffer[32]==0xa5;
 reset(1);
 void *failed = checked_calloc(4,8);
 int failure_safe = failed == NULL && null_zero_calls==0 && zero_calls==0;
 int observed_null_zero = null_zero_calls;
 reset(0);
 void *overflow = checked_calloc(SIZE_MAX/2+1,2);
 int overflow_safe = overflow == NULL && alloc_calls==0 && zero_calls==0;
 reset(0);
 void *zero = checked_calloc(0,8);
 int zero_safe = zero == NULL || (zero == buffer && null_zero_calls==0);
 printf("{\"normal_allocation_zeroed\":%s,\"oom_returns_without_memset\":%s,"
        "\"null_memset_calls_on_oom\":%d,\"multiplication_overflow_rejected\":%s,"
        "\"zero_size_valid\":%s}\n", success?"true":"false", failure_safe?"true":"false",
        observed_null_zero,overflow_safe?"true":"false",zero_safe?"true":"false");
}
'''
    with tempfile.TemporaryDirectory(prefix='h96-calloc-') as directory:
        work = Path(directory)
        (work / 'check.c').write_text(preamble + body + harness)
        subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(work / 'check.c'), '-o', str(work / 'check')], check=True)
        result = json.loads(subprocess.check_output([str(work / 'check')], text=True))
    passed = all(result[key] for key in ('normal_allocation_zeroed',
                 'oom_returns_without_memset', 'multiplication_overflow_rejected', 'zero_size_valid'))
    result['status'] = 'CHECKS_PASS' if passed else 'SOURCE_DEFECTS_REPRODUCED'
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
