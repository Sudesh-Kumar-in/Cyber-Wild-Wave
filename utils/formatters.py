import re

LINE  = "━" * 22
_SEP  = "─" * 21


# ── Value helpers ─────────────────────────────────────────────────────────────

def _val(value) -> str:
    if value in (None, "", [], {}):
        return ""
    v = str(value).strip()
    return "" if v.lower() in ("none", "null", "n/a", "nan") else v


def _field(emoji: str, label: str, value) -> str:
    v = _val(value)
    return f"{emoji} <b>{label}:</b> {v}" if v else f"{emoji} <b>{label}:</b> ❌ Data Not Found"


def _bool_field(emoji: str, label: str, value) -> str:
    """Render True/False as ✅ Available / ❌ Not Available."""
    if value is None or value == "":
        return f"{emoji} <b>{label}:</b> ❌ Data Not Found"
    if isinstance(value, bool):
        return f"{emoji} <b>{label}:</b> {'✅ Available' if value else '❌ Not Available'}"
    sv = str(value).strip().lower()
    if sv in ("true", "1", "yes"):
        return f"{emoji} <b>{label}:</b> ✅ Available"
    if sv in ("false", "0", "no"):
        return f"{emoji} <b>{label}:</b> ❌ Not Available"
    return f"{emoji} <b>{label}:</b> {value}"


def _clean_address(raw: str) -> str:
    if not raw:
        return ""
    addr = raw.replace("!!", ", ").replace("!", ", ")
    addr = re.sub(r",\s*,", ",", addr)
    addr = re.sub(r"\s{2,}", " ", addr)
    addr = re.sub(r",\s*$", "", addr.strip())
    return addr.title()


# ── Number Lookup (HTML-native card) ──────────────────────────────────────────

_COLS  = {
    "name":    ("👤", "Name   "),
    "father":  ("👨", "Father "),
    "mobile":  ("📱", "Mobile "),
    "alt":     ("📞", "Alt No "),
    "aadhar":  ("🆔", "Aadhaar"),
    "email":   ("📧", "Email  "),
    "circle":  ("📡", "Circle "),
    "address": ("🏠", "Address"),
}
_ORDER = ["name", "father", "mobile", "alt", "aadhar", "email", "circle", "address"]


def _render_record(rec: dict, idx: int = 0, total: int = 1) -> str:
    lines = [f"┌{_SEP}"]
    if total > 1:
        lines.append(f"│ 🔢 Record {idx + 1} of {total}")
        lines.append(f"│{_SEP}")

    for key in _ORDER:
        emoji, label = _COLS[key]
        raw_val = rec.get(key)
        if key == "address":
            val = _clean_address(raw_val) if raw_val else None
        else:
            val = _val(raw_val)

        if val:
            lines.append(f"│ {emoji} {label} : {val}")
        else:
            lines.append(f"│ {emoji} {label} : ❌ Data Not Found")

    lines.append(f"└{_SEP}")
    return "\n".join(lines)


def format_number_lookup(data) -> str:
    records = data if isinstance(data, list) else [data]
    total   = len(records)
    parts   = [_render_record(rec, i, total) for i, rec in enumerate(records)]
    body    = "\n\n".join(parts)
    return (
        f"📱 <b>NUMBER LOOKUP</b>\n"
        f"{LINE}\n\n"
        f"{body}\n\n"
        f"✅ <i>Search completed successfully</i>"
    )


# ── Telegram Lookup ───────────────────────────────────────────────────────────

def format_telegram_lookup(data: dict) -> str:
    return (
        f"📞 <b>TELEGRAM LOOKUP</b>\n"
        f"{LINE}\n\n"
        f"{_field('👤', 'Name',     data.get('name') or data.get('first_name'))}\n"
        f"{_field('🆔', 'User ID',  data.get('user_id') or data.get('id'))}\n"
        f"{_field('📛', 'Username', data.get('username'))}\n"
        f"{_field('📞', 'Phone',    data.get('phone') or data.get('mobile'))}\n"
        f"{_field('🗓', 'Joined',   data.get('joined') or data.get('created_at'))}\n"
        f"{_field('📝', 'Bio',      data.get('bio'))}\n\n"
        f"{LINE}\n"
        f"✅ <i>Search completed successfully</i>"
    )


# ── Aadhaar Lookup ────────────────────────────────────────────────────────────

def format_aadhaar_lookup(data: dict) -> str:
    return (
        f"🪪 <b>AADHAAR LOOKUP</b>\n"
        f"{LINE}\n\n"
        f"{_field('👤', 'Name',      data.get('name'))}\n"
        f"{_field('🆔', 'Aadhaar',   data.get('aadhaar') or data.get('aadhar_number'))}\n"
        f"{_field('📱', 'Mobile',    data.get('mobile') or data.get('phone'))}\n"
        f"{_field('🎂', 'DOB',       data.get('dob') or data.get('date_of_birth'))}\n"
        f"{_field('⚧', 'Gender',    data.get('gender'))}\n"
        f"{_field('👨', 'Father',    data.get('father') or data.get('father_name'))}\n"
        f"{_field('👩', 'Mother',    data.get('mother') or data.get('mother_name'))}\n"
        f"{_field('🏠', 'Address',   data.get('address'))}\n"
        f"{_field('📍', 'State',     data.get('state'))}\n"
        f"{_field('📮', 'Pincode',   data.get('pincode'))}\n"
        f"{_field('🏘', 'District',  data.get('district'))}\n\n"
        f"{LINE}\n"
        f"✅ <i>Search completed successfully</i>"
    )


# ── Family Lookup ─────────────────────────────────────────────────────────────

def format_family_lookup(data: dict) -> str:
    members = data.get("members") or data.get("family") or []
    lines = [
        f"👨‍👩‍👧‍👦 <b>FAMILY LOOKUP</b>",
        LINE,
        "",
        _field("👤", "Head",    data.get("head") or data.get("name")),
        _field("🆔", "Aadhaar", data.get("aadhaar")),
        _field("🏠", "Address", data.get("address")),
        _field("📍", "State",   data.get("state")),
        _field("📮", "Pincode", data.get("pincode")),
        "",
    ]
    if members:
        lines.append(f"👥 <b>Family Members ({len(members)}):</b>")
        for i, m in enumerate(members, 1):
            n   = m.get("name", "N/A")
            rel = m.get("relation", "N/A")
            dob = m.get("dob", "N/A")
            lines.append(f"  <b>{i}.</b> {n} | {rel} | {dob}")
    lines += ["", LINE, "✅ <i>Search completed successfully</i>"]
    return "\n".join(lines)


# ── Pincode Lookup ────────────────────────────────────────────────────────────

def format_pincode_lookup(data: dict) -> str:
    offices = data.get("offices") or data.get("post_offices") or []
    first   = offices[0] if offices else {}
    lines   = [
        f"📍 <b>PINCODE LOOKUP</b>",
        LINE,
        "",
        _field("📮", "Pincode",  data.get("pincode")),
        _field("📍", "State",    data.get("state") or first.get("State")),
        _field("🏘", "District", data.get("district") or first.get("District")),
        _field("🌐", "Region",   data.get("region") or first.get("Region")),
        _field("🏙", "Division", data.get("division") or first.get("Division")),
        "",
    ]
    if offices:
        lines.append(f"📋 <b>Post Offices ({min(len(offices), 10)}):</b>")
        for o in offices[:10]:
            name = o.get("Name") or o.get("name") or "N/A"
            typ  = o.get("BranchType") or o.get("type") or ""
            delv = o.get("DeliveryStatus") or o.get("delivery_status") or ""
            tag  = f" | {delv}" if delv else ""
            lines.append(f"  • <b>{name}</b> ({typ}){tag}")
    lines += ["", LINE, "✅ <i>Search completed successfully</i>"]
    return "\n".join(lines)


# ── IFSC Lookup ───────────────────────────────────────────────────────────────

def format_ifsc_lookup(data: dict) -> str:
    return (
        f"🏦 <b>IFSC LOOKUP</b>\n"
        f"{LINE}\n\n"
        f"{_field('🏦', 'Bank',     data.get('BANK') or data.get('bank'))}\n"
        f"{_field('🪙', 'IFSC',     data.get('IFSC') or data.get('ifsc'))}\n"
        f"{_field('🏢', 'Branch',   data.get('BRANCH') or data.get('branch'))}\n"
        f"{_field('🏙', 'City',     data.get('CITY') or data.get('city'))}\n"
        f"{_field('🏘', 'District', data.get('DISTRICT') or data.get('district'))}\n"
        f"{_field('📍', 'State',    data.get('STATE') or data.get('state'))}\n"
        f"{_field('🏠', 'Address',  data.get('ADDRESS') or data.get('address'))}\n"
        f"{_field('📞', 'Phone',    data.get('CONTACT') or data.get('phone'))}\n"
        f"{_field('🌐', 'MICR',     data.get('MICR') or data.get('micr'))}\n"
        f"{_bool_field('💳', 'RTGS', data.get('RTGS'))}\n"
        f"{_bool_field('🔄', 'NEFT', data.get('NEFT'))}\n"
        f"{_bool_field('📲', 'IMPS', data.get('IMPS'))}\n"
        f"{_bool_field('🏧', 'UPI',  data.get('UPI'))}\n\n"
        f"{LINE}\n"
        f"✅ <i>Search completed successfully</i>"
    )


# ── Vehicle Lookup ────────────────────────────────────────────────────────────

def format_vehicle_lookup(data: dict) -> str:
    make_model = f"{data.get('make', '')} {data.get('model', '')}".strip() or data.get("vehicle")
    return (
        f"🚗 <b>VEHICLE LOOKUP</b>\n"
        f"{LINE}\n\n"
        f"{_field('🚗', 'Reg No',       data.get('reg_no') or data.get('vehicle_number'))}\n"
        f"{_field('👤', 'Owner',        data.get('owner') or data.get('owner_name'))}\n"
        f"{_field('🚙', 'Make / Model', make_model)}\n"
        f"{_field('🎨', 'Color',        data.get('color'))}\n"
        f"{_field('📅', 'Reg Date',     data.get('reg_date') or data.get('registration_date'))}\n"
        f"{_field('📅', 'Expiry',       data.get('expiry') or data.get('fitness_upto'))}\n"
        f"{_field('⛽', 'Fuel',         data.get('fuel_type'))}\n"
        f"{_field('🏙', 'RTO',          data.get('rto') or data.get('rto_code'))}\n"
        f"{_field('📍', 'State',        data.get('state'))}\n"
        f"{_field('🏢', 'Insurance Co', data.get('insurance_company'))}\n"
        f"{_field('📅', 'Ins. Expiry',  data.get('insurance_upto'))}\n"
        f"{_field('🔢', 'Chassis No',   data.get('chassis_no'))}\n"
        f"{_field('⚙', 'Engine No',    data.get('engine_no'))}\n\n"
        f"{LINE}\n"
        f"✅ <i>Search completed successfully</i>"
    )
