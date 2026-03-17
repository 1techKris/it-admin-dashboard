# backend/app/services/service_labels.py

PORT_LABELS = {
    22: "SSH",
    80: "HTTP",
    443: "HTTPS",
    445: "SMB",
    3389: "RDP",
    9100: "JetDirect",
}

def label_for_port(port: int) -> str:
    return PORT_LABELS.get(port, f"Port {port}")