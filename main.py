from networkmapper.scanner import NetworkScanner

scanner = NetworkScanner()

subnet = input("Subnet (192.168.1.0/24): ")

devices = scanner.discover(subnet)

print(f"Found {len(devices)} device(s)\n")

for device in devices:
    print(device)