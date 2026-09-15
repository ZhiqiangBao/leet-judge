use std::collections::BTreeMap;

#[derive(Clone, Debug)]
enum JsonValue {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    Arr(Vec<JsonValue>),
    Obj(BTreeMap<String, JsonValue>),
}

struct JsonParser<'a> {
    s: &'a [u8],
    i: usize,
}

impl<'a> JsonParser<'a> {
    fn parse(text: &'a str) -> Result<JsonValue, String> {
        let mut p = JsonParser {
            s: text.as_bytes(),
            i: 0,
        };
        let v = p.value()?;
        p.skip();
        if p.i != p.s.len() {
            return Err("json: trailing data".into());
        }
        Ok(v)
    }

    fn skip(&mut self) {
        while self.i < self.s.len() && self.s[self.i].is_ascii_whitespace() {
            self.i += 1;
        }
    }

    fn value(&mut self) -> Result<JsonValue, String> {
        self.skip();
        if self.i >= self.s.len() {
            return Err("json: unexpected end".into());
        }
        match self.s[self.i] {
            b'n' => self.lit(b"null", JsonValue::Null),
            b't' => self.lit(b"true", JsonValue::Bool(true)),
            b'f' => self.lit(b"false", JsonValue::Bool(false)),
            b'"' => Ok(JsonValue::Str(self.string()?)),
            b'[' => self.array(),
            b'{' => self.object(),
            b'-' | b'0'..=b'9' => self.number(),
            _ => Err("json: invalid value".into()),
        }
    }

    fn lit(&mut self, lit: &[u8], v: JsonValue) -> Result<JsonValue, String> {
        if self.s[self.i..].len() < lit.len() || &self.s[self.i..self.i + lit.len()] != lit {
            return Err("json: invalid literal".into());
        }
        self.i += lit.len();
        Ok(v)
    }

    fn string(&mut self) -> Result<String, String> {
        self.i += 1;
        let mut out = String::new();
        while self.i < self.s.len() {
            let c = self.s[self.i];
            self.i += 1;
            if c == b'"' {
                return Ok(out);
            }
            if c == b'\\' {
                if self.i >= self.s.len() {
                    return Err("json: bad escape".into());
                }
                let e = self.s[self.i];
                self.i += 1;
                match e {
                    b'"' | b'\\' | b'/' => out.push(e as char),
                    b'n' => out.push('\n'),
                    b'r' => out.push('\r'),
                    b't' => out.push('\t'),
                    b'u' => {
                        if self.i + 4 > self.s.len() {
                            return Err("json: bad unicode".into());
                        }
                        self.i += 4;
                        out.push('?');
                    }
                    _ => return Err("json: bad escape".into()),
                }
            } else {
                out.push(c as char);
            }
        }
        Err("json: unterminated string".into())
    }

    fn number(&mut self) -> Result<JsonValue, String> {
        let start = self.i;
        let mut is_int = true;
        if self.s[self.i] == b'-' {
            self.i += 1;
        }
        while self.i < self.s.len() && self.s[self.i].is_ascii_digit() {
            self.i += 1;
        }
        if self.i < self.s.len() && self.s[self.i] == b'.' {
            is_int = false;
            self.i += 1;
            while self.i < self.s.len() && self.s[self.i].is_ascii_digit() {
                self.i += 1;
            }
        }
        if self.i < self.s.len() && (self.s[self.i] == b'e' || self.s[self.i] == b'E') {
            is_int = false;
            self.i += 1;
            if self.i < self.s.len() && (self.s[self.i] == b'+' || self.s[self.i] == b'-') {
                self.i += 1;
            }
            while self.i < self.s.len() && self.s[self.i].is_ascii_digit() {
                self.i += 1;
            }
        }
        let tok = std::str::from_utf8(&self.s[start..self.i]).unwrap();
        if is_int {
            if let Ok(n) = tok.parse::<i64>() {
                return Ok(JsonValue::Int(n));
            }
        }
        tok.parse::<f64>()
            .map(JsonValue::Float)
            .map_err(|_| "json: bad number".to_string())
    }

    fn array(&mut self) -> Result<JsonValue, String> {
        self.i += 1;
        self.skip();
        if self.i < self.s.len() && self.s[self.i] == b']' {
            self.i += 1;
            return Ok(JsonValue::Arr(Vec::new()));
        }
        let mut arr = Vec::new();
        loop {
            arr.push(self.value()?);
            self.skip();
            if self.i >= self.s.len() {
                return Err("json: unterminated array".into());
            }
            if self.s[self.i] == b']' {
                self.i += 1;
                return Ok(JsonValue::Arr(arr));
            }
            if self.s[self.i] != b',' {
                return Err("json: expected comma".into());
            }
            self.i += 1;
        }
    }

    fn object(&mut self) -> Result<JsonValue, String> {
        self.i += 1;
        self.skip();
        if self.i < self.s.len() && self.s[self.i] == b'}' {
            self.i += 1;
            return Ok(JsonValue::Obj(BTreeMap::new()));
        }
        let mut obj = BTreeMap::new();
        loop {
            self.skip();
            if self.i >= self.s.len() || self.s[self.i] != b'"' {
                return Err("json: expected key".into());
            }
            let key = self.string()?;
            self.skip();
            if self.i >= self.s.len() || self.s[self.i] != b':' {
                return Err("json: expected colon".into());
            }
            self.i += 1;
            obj.insert(key, self.value()?);
            self.skip();
            if self.i >= self.s.len() {
                return Err("json: unterminated object".into());
            }
            if self.s[self.i] == b'}' {
                self.i += 1;
                return Ok(JsonValue::Obj(obj));
            }
            if self.s[self.i] != b',' {
                return Err("json: expected comma".into());
            }
            self.i += 1;
        }
    }
}

impl JsonValue {
    fn dumps(&self) -> String {
        match self {
            JsonValue::Null => "null".into(),
            JsonValue::Bool(true) => "true".into(),
            JsonValue::Bool(false) => "false".into(),
            JsonValue::Int(n) => n.to_string(),
            JsonValue::Float(n) => {
                if n.fract() == 0.0 && n.abs() < 1e15 {
                    format!("{}", *n as i64)
                } else {
                    format!("{}", n)
                }
            }
            JsonValue::Str(s) => {
                let mut out = String::from("\"");
                for c in s.chars() {
                    match c {
                        '"' => out.push_str("\\\""),
                        '\\' => out.push_str("\\\\"),
                        '\n' => out.push_str("\\n"),
                        '\r' => out.push_str("\\r"),
                        '\t' => out.push_str("\\t"),
                        _ => out.push(c),
                    }
                }
                out.push('"');
                out
            }
            JsonValue::Arr(a) => {
                let parts: Vec<String> = a.iter().map(|x| x.dumps()).collect();
                format!("[{}]", parts.join(","))
            }
            JsonValue::Obj(o) => {
                let parts: Vec<String> = o
                    .iter()
                    .map(|(k, v)| format!("\"{}\":{}", k, v.dumps()))
                    .collect();
                format!("{{{}}}", parts.join(","))
            }
        }
    }

    fn get(&self, key: &str) -> Result<&JsonValue, String> {
        match self {
            JsonValue::Obj(o) => o
                .get(key)
                .ok_or_else(|| format!("json: missing key {key}")),
            _ => Err("json: expected object".into()),
        }
    }

    fn as_array(&self) -> Result<&[JsonValue], String> {
        match self {
            JsonValue::Arr(a) => Ok(a),
            _ => Err("json: expected array".into()),
        }
    }

    fn as_bool(&self) -> Result<bool, String> {
        match self {
            JsonValue::Bool(b) => Ok(*b),
            _ => Err("json: expected bool".into()),
        }
    }

    fn as_i32(&self) -> Result<i32, String> {
        Ok(self.as_i64()? as i32)
    }

    fn as_i64(&self) -> Result<i64, String> {
        match self {
            JsonValue::Int(n) => Ok(*n),
            JsonValue::Float(n) => Ok(*n as i64),
            _ => Err("json: expected number".into()),
        }
    }

    fn as_f64(&self) -> Result<f64, String> {
        match self {
            JsonValue::Int(n) => Ok(*n as f64),
            JsonValue::Float(n) => Ok(*n),
            _ => Err("json: expected number".into()),
        }
    }

    fn as_string(&self) -> Result<String, String> {
        match self {
            JsonValue::Str(s) => Ok(s.clone()),
            _ => Err("json: expected string".into()),
        }
    }
}

fn json_close(a: &JsonValue, b: &JsonValue) -> bool {
    match (a, b) {
        (JsonValue::Bool(x), JsonValue::Bool(y)) => x == y,
        (JsonValue::Int(x), JsonValue::Int(y)) => x == y,
        (JsonValue::Int(x), JsonValue::Float(y)) | (JsonValue::Float(y), JsonValue::Int(x)) => {
            let x = *x as f64;
            let d = (x - *y).abs();
            d <= 1e-6 || d <= 1e-6 * x.abs().max(y.abs())
        }
        (JsonValue::Float(x), JsonValue::Float(y)) => {
            let d = (x - y).abs();
            d <= 1e-6 || d <= 1e-6 * x.abs().max(y.abs())
        }
        (JsonValue::Str(x), JsonValue::Str(y)) => x == y,
        (JsonValue::Null, JsonValue::Null) => true,
        (JsonValue::Arr(x), JsonValue::Arr(y)) => {
            x.len() == y.len() && x.iter().zip(y.iter()).all(|(p, q)| json_close(p, q))
        }
        _ => false,
    }
}

fn json_equal(a: &JsonValue, b: &JsonValue, any_order: bool) -> bool {
    if any_order {
        if let (JsonValue::Arr(x), JsonValue::Arr(y)) = (a, b) {
            if x.len() != y.len() {
                return false;
            }
            let mut xs: Vec<String> = x.iter().map(|v| v.dumps()).collect();
            let mut ys: Vec<String> = y.iter().map(|v| v.dumps()).collect();
            xs.sort();
            ys.sort();
            return xs == ys;
        }
    }
    json_close(a, b)
}

fn json_from_i32(v: i32) -> JsonValue {
    JsonValue::Int(v as i64)
}
fn json_from_i64(v: i64) -> JsonValue {
    JsonValue::Int(v)
}
fn json_from_f64(v: f64) -> JsonValue {
    JsonValue::Float(v)
}
fn json_from_bool(v: bool) -> JsonValue {
    JsonValue::Bool(v)
}
fn json_from_string(v: String) -> JsonValue {
    JsonValue::Str(v)
}
fn json_from_vec<T, F>(v: Vec<T>, mut f: F) -> JsonValue
where
    F: FnMut(T) -> JsonValue,
{
    JsonValue::Arr(v.into_iter().map(|x| f(x)).collect())
}
