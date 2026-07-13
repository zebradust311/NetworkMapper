import nmap


class NetworkScanner:

    def __init__(self):
        self.scanner = nmap.PortScanner()

    def discover(self, subnet):

        print(f"\nScanning {subnet}...\n")

        self.scanner.scan(
            hosts=subnet,
            arguments="-sn"
        )

        devices = []

        for host in self.scanner.all_hosts():

            hostname = self.scanner[host].hostname()

            devices.append({
                "ip": host,
                "hostname": hostname if hostname else "Unknown",
                "state": self.scanner[host].state()
            })

        return devices