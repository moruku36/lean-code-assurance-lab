use std::io::{self, BufRead, Write};

fn reserve(capacity: u64, used: u64, request: u64) -> Option<u64> {
    used.checked_add(request).filter(|&next| next <= capacity)
}

fn main() -> io::Result<()> {
    let mut out = io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let line = line?;
        let parts: Vec<_> = line.split_ascii_whitespace().collect();
        let invalid = || io::Error::new(io::ErrorKind::InvalidData, "expected three unsigned u64 decimals");
        if parts.len() != 3 || parts.iter().any(|v| !v.bytes().all(|b| b.is_ascii_digit())) {
            return Err(invalid());
        }
        let capacity = parts[0].parse::<u64>().map_err(|_| invalid())?;
        let used = parts[1].parse::<u64>().map_err(|_| invalid())?;
        let request = parts[2].parse::<u64>().map_err(|_| invalid())?;
        match reserve(capacity, used, request) {
            Some(next) => writeln!(out, "{next}")?,
            None => writeln!(out, "reject")?,
        }
    }
    out.flush()
}
