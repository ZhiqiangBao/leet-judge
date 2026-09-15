#ifndef LOCAL_LEET_JSON_H
#define LOCAL_LEET_JSON_H

#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum { J_NIL, J_BOOL, J_NUM, J_STR, J_ARR, J_OBJ } JType;

typedef struct JsonValue JsonValue;
struct JsonValue {
    JType type;
    bool b;
    bool is_int;
    double n;
    long long i;
    char *s;
    JsonValue *a;
    int alen;
    char **okeys;
    JsonValue *ovals;
    int olen;
};

static void json_die(const char *msg) {
    fprintf(stderr, "%s\n", msg);
    exit(1);
}

static void skip_ws(const char *t, int *i) {
    while (t[*i] && isspace((unsigned char)t[*i])) (*i)++;
}

static JsonValue json_null(void) {
    JsonValue v;
    memset(&v, 0, sizeof(v));
    v.type = J_NIL;
    return v;
}

static JsonValue json_bool(bool b) {
    JsonValue v = json_null();
    v.type = J_BOOL;
    v.b = b;
    return v;
}

static JsonValue json_num(double n) {
    JsonValue v = json_null();
    v.type = J_NUM;
    v.n = n;
    return v;
}

static JsonValue json_str(const char *s) {
    JsonValue v = json_null();
    v.type = J_STR;
    v.s = strdup(s ? s : "");
    return v;
}

static JsonValue json_arr(void) {
    JsonValue v = json_null();
    v.type = J_ARR;
    return v;
}

static JsonValue parse_value(const char *t, int *i);

static char *parse_string(const char *t, int *i) {
    if (t[*i] != '"') json_die("json: expected string");
    (*i)++;
    char *out = (char *)malloc(strlen(t) + 1);
    int n = 0;
    while (t[*i] && t[*i] != '"') {
        if (t[*i] == '\\') {
            (*i)++;
            char e = t[*i];
            if (e == '"' || e == '\\' || e == '/') out[n++] = e;
            else if (e == 'n') out[n++] = '\n';
            else if (e == 'r') out[n++] = '\r';
            else if (e == 't') out[n++] = '\t';
            else if (e == 'u') {
                *i += 4;
                out[n++] = '?';
            }
            (*i)++;
        } else {
            out[n++] = t[(*i)++];
        }
    }
    if (t[*i] != '"') json_die("json: unterminated string");
    (*i)++;
    out[n] = 0;
    return out;
}

static JsonValue json_from_long(long long n) {
    JsonValue v = json_null();
    v.type = J_NUM;
    v.is_int = true;
    v.i = n;
    v.n = (double)n;
    return v;
}

static JsonValue parse_number(const char *t, int *i) {
    int start = *i;
    int is_int = 1;
    if (t[*i] == '-') (*i)++;
    if (!isdigit((unsigned char)t[*i])) {
        json_die("json: invalid number");
    }
    while (t[*i] && isdigit((unsigned char)t[*i])) (*i)++;
    if (t[*i] == '.') {
        is_int = 0;
        (*i)++;
        while (t[*i] && isdigit((unsigned char)t[*i])) (*i)++;
    }
    if (t[*i] == 'e' || t[*i] == 'E') {
        is_int = 0;
        (*i)++;
        if (t[*i] == '+' || t[*i] == '-') (*i)++;
        while (t[*i] && isdigit((unsigned char)t[*i])) (*i)++;
    }
    if (is_int) {
        errno = 0;
        long long v = strtoll(t + start, NULL, 10);
        if (errno != ERANGE) return json_from_long(v);
    }
    return json_num(strtod(t + start, NULL));
}

static JsonValue parse_array(const char *t, int *i) {
    (*i)++;
    JsonValue arr = json_arr();
    skip_ws(t, i);
    if (t[*i] == ']') {
        (*i)++;
        return arr;
    }
    while (1) {
        JsonValue item = parse_value(t, i);
        arr.a = (JsonValue *)realloc(arr.a, sizeof(JsonValue) * (arr.alen + 1));
        arr.a[arr.alen++] = item;
        skip_ws(t, i);
        if (t[*i] == ']') {
            (*i)++;
            return arr;
        }
        if (t[*i] != ',') json_die("json: expected comma");
        (*i)++;
    }
}

static JsonValue parse_object(const char *t, int *i) {
    (*i)++;
    JsonValue obj = json_null();
    obj.type = J_OBJ;
    skip_ws(t, i);
    if (t[*i] == '}') {
        (*i)++;
        return obj;
    }
    while (1) {
        skip_ws(t, i);
        char *key = parse_string(t, i);
        skip_ws(t, i);
        if (t[*i] != ':') json_die("json: expected colon");
        (*i)++;
        JsonValue val = parse_value(t, i);
        obj.okeys = (char **)realloc(obj.okeys, sizeof(char *) * (obj.olen + 1));
        obj.ovals = (JsonValue *)realloc(obj.ovals, sizeof(JsonValue) * (obj.olen + 1));
        obj.okeys[obj.olen] = key;
        obj.ovals[obj.olen] = val;
        obj.olen++;
        skip_ws(t, i);
        if (t[*i] == '}') {
            (*i)++;
            return obj;
        }
        if (t[*i] != ',') json_die("json: expected comma");
        (*i)++;
    }
}

static JsonValue parse_value(const char *t, int *i) {
    skip_ws(t, i);
    char c = t[*i];
    if (c == 'n') {
        *i += 4;
        return json_null();
    }
    if (c == 't') {
        *i += 4;
        return json_bool(true);
    }
    if (c == 'f') {
        *i += 5;
        return json_bool(false);
    }
    if (c == '"') {
        JsonValue v = json_null();
        v.type = J_STR;
        v.s = parse_string(t, i);
        return v;
    }
    if (c == '[') return parse_array(t, i);
    if (c == '{') return parse_object(t, i);
    if (c == '-' || isdigit((unsigned char)c)) return parse_number(t, i);
    json_die("json: invalid value");
    return json_null();
}

static JsonValue json_parse(const char *t) {
    int i = 0;
    JsonValue v = parse_value(t, &i);
    skip_ws(t, &i);
    return v;
}

static const JsonValue *json_get(const JsonValue *v, const char *key) {
    if (v->type != J_OBJ) json_die("json: expected object");
    for (int i = 0; i < v->olen; i++) {
        if (strcmp(v->okeys[i], key) == 0) return &v->ovals[i];
    }
    json_die("json: missing key");
    return NULL;
}

static const JsonValue *json_at(const JsonValue *v, int i) {
    if (v->type != J_ARR || i < 0 || i >= v->alen) json_die("json: array index");
    return &v->a[i];
}

static long long json_as_long(const JsonValue *v) {
    if (v->type != J_NUM) json_die("json: expected number");
    if (v->is_int) return v->i;
    return (long long)v->n;
}

static int json_as_int(const JsonValue *v) {
    return (int)json_as_long(v);
}

static double json_as_double(const JsonValue *v) {
    if (v->type != J_NUM) json_die("json: expected number");
    return v->n;
}

static bool json_as_bool(const JsonValue *v) {
    if (v->type != J_BOOL) json_die("json: expected bool");
    return v->b;
}

static char *json_as_cstr(const JsonValue *v) {
    if (v->type != J_STR) json_die("json: expected string");
    return v->s;
}

static int *json_as_int_array(const JsonValue *v, int *n) {
    if (v->type != J_ARR) json_die("json: expected array");
    *n = v->alen;
    int *p = (int *)malloc(sizeof(int) * (*n == 0 ? 1 : *n));
    for (int i = 0; i < *n; i++) p[i] = json_as_int(&v->a[i]);
    return p;
}

static long long *json_as_long_array(const JsonValue *v, int *n) {
    if (v->type != J_ARR) json_die("json: expected array");
    *n = v->alen;
    long long *p = (long long *)malloc(sizeof(long long) * (*n == 0 ? 1 : *n));
    for (int i = 0; i < *n; i++) p[i] = json_as_long(&v->a[i]);
    return p;
}

static char **json_as_str_array(const JsonValue *v, int *n) {
    if (v->type != J_ARR) json_die("json: expected array");
    *n = v->alen;
    char **p = (char **)malloc(sizeof(char *) * (*n == 0 ? 1 : *n));
    for (int i = 0; i < *n; i++) p[i] = json_as_cstr(&v->a[i]);
    return p;
}

static double *json_as_double_array(const JsonValue *v, int *n) {
    if (v->type != J_ARR) json_die("json: expected array");
    *n = v->alen;
    double *p = (double *)malloc(sizeof(double) * (*n == 0 ? 1 : *n));
    for (int i = 0; i < *n; i++) p[i] = json_as_double(&v->a[i]);
    return p;
}

static bool *json_as_bool_array(const JsonValue *v, int *n) {
    if (v->type != J_ARR) json_die("json: expected array");
    *n = v->alen;
    bool *p = (bool *)malloc(sizeof(bool) * (*n == 0 ? 1 : *n));
    for (int i = 0; i < *n; i++) p[i] = json_as_bool(&v->a[i]);
    return p;
}

static void json_write(const JsonValue *v, FILE *out);

static void json_write(const JsonValue *v, FILE *out) {
    switch (v->type) {
        case J_NIL:
            fputs("null", out);
            break;
        case J_BOOL:
            fputs(v->b ? "true" : "false", out);
            break;
        case J_NUM:
            if (v->is_int)
                fprintf(out, "%lld", v->i);
            else if (floor(v->n) == v->n && fabs(v->n) < 1e15)
                fprintf(out, "%lld", (long long)v->n);
            else
                fprintf(out, "%.10g", v->n);
            break;
        case J_STR:
            fputc('"', out);
            for (const char *p = v->s ? v->s : ""; *p; p++) {
                if (*p == '"' || *p == '\\') fputc('\\', out);
                fputc(*p, out);
            }
            fputc('"', out);
            break;
        case J_ARR:
            fputc('[', out);
            for (int i = 0; i < v->alen; i++) {
                if (i) fputc(',', out);
                json_write(&v->a[i], out);
            }
            fputc(']', out);
            break;
        case J_OBJ:
            fputc('{', out);
            for (int i = 0; i < v->olen; i++) {
                if (i) fputc(',', out);
                fprintf(out, "\"%s\":", v->okeys[i]);
                json_write(&v->ovals[i], out);
            }
            fputc('}', out);
            break;
    }
}

static char *json_dumps(const JsonValue *v) {
    FILE *tmp = tmpfile();
    if (!tmp) json_die("json: tmpfile");
    json_write(v, tmp);
    long n = ftell(tmp);
    if (n < 0) n = 0;
    rewind(tmp);
    char *buf = (char *)malloc((size_t)n + 1);
    size_t got = fread(buf, 1, (size_t)n, tmp);
    buf[got] = 0;
    fclose(tmp);
    return buf;
}

static int cmp_strptr(const void *a, const void *b) {
    return strcmp(*(char *const *)a, *(char *const *)b);
}

static bool json_equal(const JsonValue *a, const JsonValue *b, bool any_order) {
    if (a->type != b->type) {
        if (a->type == J_NUM && b->type == J_NUM) return fabs(a->n - b->n) <= 1e-6;
        return false;
    }
    switch (a->type) {
        case J_NIL:
            return true;
        case J_BOOL:
            return a->b == b->b;
        case J_NUM:
            if (a->is_int && b->is_int) return a->i == b->i;
            return fabs(a->n - b->n) <= 1e-6;
        case J_STR:
            return strcmp(a->s ? a->s : "", b->s ? b->s : "") == 0;
        case J_ARR:
            if (a->alen != b->alen) return false;
            if (any_order) {
                char **as = (char **)malloc(sizeof(char *) * a->alen);
                char **bs = (char **)malloc(sizeof(char *) * b->alen);
                for (int i = 0; i < a->alen; i++) {
                    as[i] = json_dumps(&a->a[i]);
                    bs[i] = json_dumps(&b->a[i]);
                }
                qsort(as, a->alen, sizeof(char *), cmp_strptr);
                qsort(bs, b->alen, sizeof(char *), cmp_strptr);
                bool ok = true;
                for (int i = 0; i < a->alen; i++)
                    if (strcmp(as[i], bs[i]) != 0) ok = false;
                for (int i = 0; i < a->alen; i++) {
                    free(as[i]);
                    free(bs[i]);
                }
                free(as);
                free(bs);
                return ok;
            }
            for (int i = 0; i < a->alen; i++)
                if (!json_equal(&a->a[i], &b->a[i], false)) return false;
            return true;
        case J_OBJ:
            if (a->olen != b->olen) return false;
            for (int i = 0; i < a->olen; i++) {
                const JsonValue *ov = NULL;
                for (int j = 0; j < b->olen; j++)
                    if (strcmp(a->okeys[i], b->okeys[j]) == 0) ov = &b->ovals[j];
                if (!ov || !json_equal(&a->ovals[i], ov, false)) return false;
            }
            return true;
    }
    return false;
}

static JsonValue json_from_int(int n) { return json_from_long((long long)n); }
static JsonValue json_from_bool(bool b) { return json_bool(b); }
static JsonValue json_from_cstr(const char *s) { return json_str(s ? s : ""); }

static JsonValue json_from_int_array(const int *p, int n) {
    JsonValue arr = json_arr();
    arr.alen = (n < 0 || p == NULL) ? 0 : n;
    arr.a = (JsonValue *)malloc(sizeof(JsonValue) * (arr.alen == 0 ? 1 : arr.alen));
    for (int i = 0; i < arr.alen; i++) arr.a[i] = json_from_int(p[i]);
    return arr;
}

static JsonValue json_from_long_array(const long long *p, int n) {
    JsonValue arr = json_arr();
    arr.alen = (n < 0 || p == NULL) ? 0 : n;
    arr.a = (JsonValue *)malloc(sizeof(JsonValue) * (arr.alen == 0 ? 1 : arr.alen));
    for (int i = 0; i < arr.alen; i++) arr.a[i] = json_from_long(p[i]);
    return arr;
}

static JsonValue json_from_str_array(char **p, int n) {
    JsonValue arr = json_arr();
    arr.alen = (n < 0 || p == NULL) ? 0 : n;
    arr.a = (JsonValue *)malloc(sizeof(JsonValue) * (arr.alen == 0 ? 1 : arr.alen));
    for (int i = 0; i < arr.alen; i++) arr.a[i] = json_from_cstr(p[i]);
    return arr;
}

static JsonValue json_from_double_array(const double *p, int n) {
    JsonValue arr = json_arr();
    arr.alen = (n < 0 || p == NULL) ? 0 : n;
    arr.a = (JsonValue *)malloc(sizeof(JsonValue) * (arr.alen == 0 ? 1 : arr.alen));
    for (int i = 0; i < arr.alen; i++) arr.a[i] = json_num(p[i]);
    return arr;
}

static JsonValue json_from_bool_array(const bool *p, int n) {
    JsonValue arr = json_arr();
    arr.alen = (n < 0 || p == NULL) ? 0 : n;
    arr.a = (JsonValue *)malloc(sizeof(JsonValue) * (arr.alen == 0 ? 1 : arr.alen));
    for (int i = 0; i < arr.alen; i++) arr.a[i] = json_from_bool(p[i]);
    return arr;
}

static int **json_as_int_matrix(const JsonValue *v, int *n, int **col_size) {
    if (v->type != J_ARR) json_die("json: expected array");
    *n = v->alen;
    int cap = (*n == 0) ? 1 : *n;
    int **p = (int **)malloc(sizeof(int *) * cap);
    int *cols = (int *)malloc(sizeof(int) * cap);
    for (int i = 0; i < *n; i++) p[i] = json_as_int_array(&v->a[i], &cols[i]);
    if (*n == 0) {
        p[0] = (int *)malloc(sizeof(int));
        cols[0] = 0;
    }
    *col_size = cols;
    return p;
}

static long long **json_as_long_matrix(const JsonValue *v, int *n, int **col_size) {
    if (v->type != J_ARR) json_die("json: expected array");
    *n = v->alen;
    int cap = (*n == 0) ? 1 : *n;
    long long **p = (long long **)malloc(sizeof(long long *) * cap);
    int *cols = (int *)malloc(sizeof(int) * cap);
    for (int i = 0; i < *n; i++) p[i] = json_as_long_array(&v->a[i], &cols[i]);
    if (*n == 0) {
        p[0] = (long long *)malloc(sizeof(long long));
        cols[0] = 0;
    }
    *col_size = cols;
    return p;
}

static char ***json_as_str_matrix(const JsonValue *v, int *n, int **col_size) {
    if (v->type != J_ARR) json_die("json: expected array");
    *n = v->alen;
    int cap = (*n == 0) ? 1 : *n;
    char ***p = (char ***)malloc(sizeof(char **) * cap);
    int *cols = (int *)malloc(sizeof(int) * cap);
    for (int i = 0; i < *n; i++) p[i] = json_as_str_array(&v->a[i], &cols[i]);
    if (*n == 0) {
        p[0] = (char **)malloc(sizeof(char *));
        cols[0] = 0;
    }
    *col_size = cols;
    return p;
}

static double **json_as_double_matrix(const JsonValue *v, int *n, int **col_size) {
    if (v->type != J_ARR) json_die("json: expected array");
    *n = v->alen;
    int cap = (*n == 0) ? 1 : *n;
    double **p = (double **)malloc(sizeof(double *) * cap);
    int *cols = (int *)malloc(sizeof(int) * cap);
    for (int i = 0; i < *n; i++) p[i] = json_as_double_array(&v->a[i], &cols[i]);
    if (*n == 0) {
        p[0] = (double *)malloc(sizeof(double));
        cols[0] = 0;
    }
    *col_size = cols;
    return p;
}

static bool **json_as_bool_matrix(const JsonValue *v, int *n, int **col_size) {
    if (v->type != J_ARR) json_die("json: expected array");
    *n = v->alen;
    int cap = (*n == 0) ? 1 : *n;
    bool **p = (bool **)malloc(sizeof(bool *) * cap);
    int *cols = (int *)malloc(sizeof(int) * cap);
    for (int i = 0; i < *n; i++) p[i] = json_as_bool_array(&v->a[i], &cols[i]);
    if (*n == 0) {
        p[0] = (bool *)malloc(sizeof(bool));
        cols[0] = 0;
    }
    *col_size = cols;
    return p;
}

static JsonValue json_from_int_matrix(int **p, int n, const int *col_size) {
    JsonValue arr = json_arr();
    arr.alen = (n < 0 || p == NULL) ? 0 : n;
    arr.a = (JsonValue *)malloc(sizeof(JsonValue) * (arr.alen == 0 ? 1 : arr.alen));
    for (int i = 0; i < arr.alen; i++) {
        int cn = col_size ? col_size[i] : 0;
        arr.a[i] = json_from_int_array(p[i], cn);
    }
    return arr;
}

static JsonValue json_from_long_matrix(long long **p, int n, const int *col_size) {
    JsonValue arr = json_arr();
    arr.alen = (n < 0 || p == NULL) ? 0 : n;
    arr.a = (JsonValue *)malloc(sizeof(JsonValue) * (arr.alen == 0 ? 1 : arr.alen));
    for (int i = 0; i < arr.alen; i++) {
        int cn = col_size ? col_size[i] : 0;
        arr.a[i] = json_from_long_array(p[i], cn);
    }
    return arr;
}

static JsonValue json_from_str_matrix(char ***p, int n, const int *col_size) {
    JsonValue arr = json_arr();
    arr.alen = (n < 0 || p == NULL) ? 0 : n;
    arr.a = (JsonValue *)malloc(sizeof(JsonValue) * (arr.alen == 0 ? 1 : arr.alen));
    for (int i = 0; i < arr.alen; i++) {
        int cn = col_size ? col_size[i] : 0;
        arr.a[i] = json_from_str_array(p[i], cn);
    }
    return arr;
}

static JsonValue json_from_double_matrix(double **p, int n, const int *col_size) {
    JsonValue arr = json_arr();
    arr.alen = (n < 0 || p == NULL) ? 0 : n;
    arr.a = (JsonValue *)malloc(sizeof(JsonValue) * (arr.alen == 0 ? 1 : arr.alen));
    for (int i = 0; i < arr.alen; i++) {
        int cn = col_size ? col_size[i] : 0;
        arr.a[i] = json_from_double_array(p[i], cn);
    }
    return arr;
}

static JsonValue json_from_bool_matrix(bool **p, int n, const int *col_size) {
    JsonValue arr = json_arr();
    arr.alen = (n < 0 || p == NULL) ? 0 : n;
    arr.a = (JsonValue *)malloc(sizeof(JsonValue) * (arr.alen == 0 ? 1 : arr.alen));
    for (int i = 0; i < arr.alen; i++) {
        int cn = col_size ? col_size[i] : 0;
        arr.a[i] = json_from_bool_array(p[i], cn);
    }
    return arr;
}

#endif
