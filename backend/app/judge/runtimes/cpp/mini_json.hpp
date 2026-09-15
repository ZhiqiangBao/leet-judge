#pragma once

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

class JsonValue {
public:
    enum Type { NIL, BOOL, NUM, STR, ARR, OBJ };

    Type type = NIL;
    bool b = false;
    bool is_int = false;
    double n = 0;
    long long i = 0;
    std::string s;
    std::vector<JsonValue> a;
    std::map<std::string, JsonValue> o;

    static JsonValue null() { return JsonValue(); }
    static JsonValue from_bool(bool v) {
        JsonValue j;
        j.type = BOOL;
        j.b = v;
        return j;
    }
    static JsonValue from_num(double v) {
        JsonValue j;
        j.type = NUM;
        j.n = v;
        return j;
    }
    static JsonValue from_long(long long v) {
        JsonValue j;
        j.type = NUM;
        j.is_int = true;
        j.i = v;
        j.n = static_cast<double>(v);
        return j;
    }
    static JsonValue from_str(const std::string& v) {
        JsonValue j;
        j.type = STR;
        j.s = v;
        return j;
    }
    static JsonValue array() {
        JsonValue j;
        j.type = ARR;
        return j;
    }

    bool as_bool() const {
        if (type != BOOL) throw std::runtime_error("json: expected bool");
        return b;
    }
    int as_int() const {
        if (type != NUM) throw std::runtime_error("json: expected number");
        if (is_int) return static_cast<int>(i);
        return static_cast<int>(n);
    }
    long long as_long() const {
        if (type != NUM) throw std::runtime_error("json: expected number");
        if (is_int) return i;
        return static_cast<long long>(n);
    }
    double as_double() const {
        if (type != NUM) throw std::runtime_error("json: expected number");
        return n;
    }
    const std::string& as_string() const {
        if (type != STR) throw std::runtime_error("json: expected string");
        return s;
    }
    const std::vector<JsonValue>& as_array() const {
        if (type != ARR) throw std::runtime_error("json: expected array");
        return a;
    }

    const JsonValue& operator[](size_t i) const {
        if (type != ARR || i >= a.size()) throw std::runtime_error("json: array index");
        return a[i];
    }
    const JsonValue& operator[](const std::string& key) const {
        if (type != OBJ) throw std::runtime_error("json: expected object");
        auto it = o.find(key);
        if (it == o.end()) throw std::runtime_error("json: missing key " + key);
        return it->second;
    }

    std::string dumps() const {
        std::ostringstream out;
        write(out);
        return out.str();
    }

    static JsonValue parse(const std::string& text) {
        size_t i = 0;
        JsonValue v = parse_value(text, i);
        skip(text, i);
        if (i != text.size()) throw std::runtime_error("json: trailing data");
        return v;
    }

private:
    void write(std::ostringstream& out) const {
        switch (type) {
            case NIL:
                out << "null";
                break;
            case BOOL:
                out << (b ? "true" : "false");
                break;
            case NUM:
                if (is_int) {
                    out << i;
                } else if (std::floor(n) == n && std::abs(n) < 1e15) {
                    out << static_cast<long long>(n);
                } else {
                    out << n;
                }
                break;
            case STR:
                out << '"' << escape(s) << '"';
                break;
            case ARR: {
                out << '[';
                for (size_t i = 0; i < a.size(); ++i) {
                    if (i) out << ',';
                    a[i].write(out);
                }
                out << ']';
                break;
            }
            case OBJ: {
                out << '{';
                bool first = true;
                for (const auto& kv : o) {
                    if (!first) out << ',';
                    first = false;
                    out << '"' << escape(kv.first) << "\":";
                    kv.second.write(out);
                }
                out << '}';
                break;
            }
        }
    }

    static std::string escape(const std::string& in) {
        std::string out;
        for (char c : in) {
            switch (c) {
                case '"': out += "\\\""; break;
                case '\\': out += "\\\\"; break;
                case '\n': out += "\\n"; break;
                case '\r': out += "\\r"; break;
                case '\t': out += "\\t"; break;
                default: out += c; break;
            }
        }
        return out;
    }

    static void skip(const std::string& t, size_t& i) {
        while (i < t.size() && std::isspace(static_cast<unsigned char>(t[i]))) ++i;
    }

    static JsonValue parse_value(const std::string& t, size_t& i) {
        skip(t, i);
        if (i >= t.size()) throw std::runtime_error("json: unexpected end");
        char c = t[i];
        if (c == 'n') return parse_lit(t, i, "null", JsonValue::null());
        if (c == 't') return parse_lit(t, i, "true", JsonValue::from_bool(true));
        if (c == 'f') return parse_lit(t, i, "false", JsonValue::from_bool(false));
        if (c == '"') return JsonValue::from_str(parse_string(t, i));
        if (c == '[') return parse_array(t, i);
        if (c == '{') return parse_object(t, i);
        if (c == '-' || std::isdigit(static_cast<unsigned char>(c))) return parse_number(t, i);
        throw std::runtime_error("json: invalid value");
    }

    static JsonValue parse_lit(const std::string& t, size_t& i, const char* lit, JsonValue v) {
        size_t n = std::char_traits<char>::length(lit);
        if (t.compare(i, n, lit) != 0) throw std::runtime_error("json: invalid literal");
        i += n;
        return v;
    }

    static std::string parse_string(const std::string& t, size_t& i) {
        ++i;
        std::string out;
        while (i < t.size()) {
            char c = t[i++];
            if (c == '"') return out;
            if (c == '\\') {
                if (i >= t.size()) throw std::runtime_error("json: bad escape");
                char e = t[i++];
                if (e == '"' || e == '\\' || e == '/') out += e;
                else if (e == 'n') out += '\n';
                else if (e == 'r') out += '\r';
                else if (e == 't') out += '\t';
                else if (e == 'u') {
                    if (i + 4 > t.size()) throw std::runtime_error("json: bad unicode");
                    i += 4;
                    out += '?';
                } else {
                    throw std::runtime_error("json: bad escape");
                }
            } else {
                out += c;
            }
        }
        throw std::runtime_error("json: unterminated string");
    }

    static JsonValue parse_number(const std::string& t, size_t& i) {
        size_t start = i;
        bool is_int = true;
        if (t[i] == '-') ++i;
        while (i < t.size() && std::isdigit(static_cast<unsigned char>(t[i]))) ++i;
        if (i < t.size() && t[i] == '.') {
            is_int = false;
            ++i;
            while (i < t.size() && std::isdigit(static_cast<unsigned char>(t[i]))) ++i;
        }
        if (i < t.size() && (t[i] == 'e' || t[i] == 'E')) {
            is_int = false;
            ++i;
            if (i < t.size() && (t[i] == '+' || t[i] == '-')) ++i;
            while (i < t.size() && std::isdigit(static_cast<unsigned char>(t[i]))) ++i;
        }
        std::string tok = t.substr(start, i - start);
        if (is_int) {
            try {
                return JsonValue::from_long(std::stoll(tok));
            } catch (...) {
                return JsonValue::from_num(std::stod(tok));
            }
        }
        return JsonValue::from_num(std::stod(tok));
    }

    static JsonValue parse_array(const std::string& t, size_t& i) {
        ++i;
        JsonValue arr = JsonValue::array();
        skip(t, i);
        if (i < t.size() && t[i] == ']') {
            ++i;
            return arr;
        }
        while (true) {
            arr.a.push_back(parse_value(t, i));
            skip(t, i);
            if (i >= t.size()) throw std::runtime_error("json: unterminated array");
            if (t[i] == ']') {
                ++i;
                return arr;
            }
            if (t[i] != ',') throw std::runtime_error("json: expected comma");
            ++i;
        }
    }

    static JsonValue parse_object(const std::string& t, size_t& i) {
        ++i;
        JsonValue obj;
        obj.type = OBJ;
        skip(t, i);
        if (i < t.size() && t[i] == '}') {
            ++i;
            return obj;
        }
        while (true) {
            skip(t, i);
            if (i >= t.size() || t[i] != '"') throw std::runtime_error("json: expected key");
            std::string key = parse_string(t, i);
            skip(t, i);
            if (i >= t.size() || t[i] != ':') throw std::runtime_error("json: expected colon");
            ++i;
            obj.o.emplace(key, parse_value(t, i));
            skip(t, i);
            if (i >= t.size()) throw std::runtime_error("json: unterminated object");
            if (t[i] == '}') {
                ++i;
                return obj;
            }
            if (t[i] != ',') throw std::runtime_error("json: expected comma");
            ++i;
        }
    }
};

inline bool json_equal(const JsonValue& a, const JsonValue& b, bool any_order) {
    if (a.type != b.type) {
        if (a.type == JsonValue::NUM && b.type == JsonValue::NUM) {
            return std::fabs(a.n - b.n) <= 1e-6;
        }
        return false;
    }
    switch (a.type) {
        case JsonValue::NIL:
            return true;
        case JsonValue::BOOL:
            return a.b == b.b;
        case JsonValue::NUM:
            if (a.is_int && b.is_int) return a.i == b.i;
            return std::fabs(a.n - b.n) <= 1e-6;
        case JsonValue::STR:
            return a.s == b.s;
        case JsonValue::ARR: {
            if (a.a.size() != b.a.size()) return false;
            if (any_order) {
                std::vector<std::string> as, bs;
                for (const auto& x : a.a) as.push_back(x.dumps());
                for (const auto& x : b.a) bs.push_back(x.dumps());
                std::sort(as.begin(), as.end());
                std::sort(bs.begin(), bs.end());
                return as == bs;
            }
            for (size_t i = 0; i < a.a.size(); ++i) {
                if (!json_equal(a.a[i], b.a[i], false)) return false;
            }
            return true;
        }
        case JsonValue::OBJ: {
            if (a.o.size() != b.o.size()) return false;
            for (const auto& kv : a.o) {
                auto it = b.o.find(kv.first);
                if (it == b.o.end() || !json_equal(kv.second, it->second, false)) return false;
            }
            return true;
        }
    }
    return false;
}

inline JsonValue to_json_val(int v) { return JsonValue::from_long(v); }
inline JsonValue to_json_val(long long v) { return JsonValue::from_long(v); }
inline JsonValue to_json_val(double v) { return JsonValue::from_num(v); }
inline JsonValue to_json_val(bool v) { return JsonValue::from_bool(v); }
inline JsonValue to_json_val(const std::string& v) { return JsonValue::from_str(v); }

template <typename T>
inline JsonValue to_json_val(const std::vector<T>& v) {
    JsonValue arr = JsonValue::array();
    for (const auto& x : v) arr.a.push_back(to_json_val(x));
    return arr;
}
