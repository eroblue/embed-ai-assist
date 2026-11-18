#ifndef S8_CASE_H
#define S8_CASE_H

#include <stdio.h>

static int s8_case(const char *id, int passed)
{
    printf("S8_CASE\t%s\t%s\n", id, passed ? "PASS" : "FAIL");
    return passed ? 0 : 1;
}

#endif
