from typing import List

from nautobot.apps.jobs import BooleanVar, Job, PasswordVar, StringVar, register_jobs
from nautobot.dcim.models import Device

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException


class EnableHttpServicesOnTaggedDevices(Job):
    """Enable HTTP/HTTPS services on devices tagged GC_Demo_Conf."""

    username = StringVar(
        description="SSH username for the target devices."
    )
    password = PasswordVar(
        description="SSH password for the target devices."
    )
    dry_run = BooleanVar(
        default=True,
        description="If enabled, only report which devices would be updated."
    )

    class Meta:
        name = "Enable HTTP/HTTPS on GC_Demo_Conf Devices"
        description = (
            "Find all devices tagged GC_Demo_Conf, enable ip http server and "
            "ip http secure-server, then save the config."
        )
        approval_required = False
        has_sensitive_variables = True

    def get_target_devices(self):
        return Device.objects.filter(tags__name="GC_Demo_Conf").distinct().order_by("name")

    def get_device_host(self, device):
        primary_ip = device.primary_ip4 or device.primary_ip6
        if not primary_ip:
            return None
        return str(primary_ip.address.ip)

    def build_netmiko_params(self, host, username, password):
        return {
            "device_type": "cisco_ios",
            "host": host,
            "username": username,
            "password": password,
            "fast_cli": False,
        }

    def run(self, *, username, password, dry_run):
        config_commands = [
            "ip http server",
            "ip http secure-server",
        ]

        save_command = "copy running-config startup-config"

        devices = self.get_target_devices()
        device_count = devices.count()

        self.logger.info("Found %s device(s) tagged with GC_Demo_Conf.", device_count)

        if device_count == 0:
            return "No devices found with tag GC_Demo_Conf."

        updated_devices: List[str] = []
        skipped_devices: List[str] = []
        failed_devices: List[str] = []

        for device in devices:
            host = self.get_device_host(device)

            if not host:
                self.logger.warning(
                    "Skipping %s because it does not have a primary IP address.",
                    device.name,
                )
                skipped_devices.append(f"{device.name} (no primary IP)")
                continue

            if dry_run:
                self.logger.info(
                    "Dry run: device %s (%s) would receive commands: %s, %s",
                    device.name,
                    host,
                    ", ".join(config_commands),
                    save_command,
                )
                updated_devices.append(device.name)
                continue

            try:
                self.logger.info("Connecting to %s (%s).", device.name, host)

                connection = ConnectHandler(
                    **self.build_netmiko_params(
                        host=host,
                        username=username,
                        password=password,
                    )
                )

                config_output = connection.send_config_set(config_commands)
                self.logger.info(
                    "Applied config to %s. Output: %s",
                    device.name,
                    config_output,
                )

                save_output = connection.save_config()
                self.logger.info(
                    "Saved config on %s. Output: %s",
                    device.name,
                    save_output,
                )

                connection.disconnect()
                updated_devices.append(device.name)

            except (NetmikoAuthenticationException, NetmikoTimeoutException) as exc:
                self.logger.error(
                    "Connection failure on %s (%s): %s",
                    device.name,
                    host,
                    exc,
                )
                failed_devices.append(f"{device.name} ({exc})")

            except Exception as exc:
                self.logger.error(
                    "Unexpected failure on %s (%s): %s",
                    device.name,
                    host,
                    exc,
                )
                failed_devices.append(f"{device.name} ({exc})")

        summary = [
            f"Processed {device_count} tagged device(s).",
            f"Updated: {len(updated_devices)}",
            f"Skipped: {len(skipped_devices)}",
            f"Failed: {len(failed_devices)}",
        ]

        if updated_devices:
            summary.append("Devices updated or targeted:")
            summary.extend([f"- {name}" for name in updated_devices])

        if skipped_devices:
            summary.append("Devices skipped:")
            summary.extend([f"- {name}" for name in skipped_devices])

        if failed_devices:
            summary.append("Devices failed:")
            summary.extend([f"- {name}" for name in failed_devices])

        result = "\n".join(summary)
        self.logger.info("%s", result)
        return result


register_jobs(EnableHttpServicesOnTaggedDevices)