from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import Device, Platform
from nautobot.tenancy.models import Tenant

class SetNtcTenantAndIosPlatform(Job):
    class Meta:
        name = "Set Tenant and Platform with Failsafe"
        description = (
            "Updates tenant to 'Network to Code' and platform to 'Cisco IOS' for devices with hostname "
            "containing 'jcy-bb' or 'jcy-rtr' (case-insensitive). Aborts if more than 3 devices match."
        )

    def run(self):
        # Retrieve the required tenant
        try:
            ntc_tenant = Tenant.objects.get(name__iexact="Network to Code")
        except Tenant.DoesNotExist:
            self.logger.error("Tenant 'Network to Code' does not exist. Please create it first.")
            return "Tenant 'Network to Code' not found, job aborted."

        # Retrieve the required platform
        try:
            ios_platform = Platform.objects.get(name__iexact="Cisco IOS")
        except Platform.DoesNotExist:
            self.logger.error("Platform 'Cisco IOS' does not exist. Please create it first.")
            return "Platform 'Cisco IOS' not found, job aborted."
        
        # Find matching devices
        matching_devices = Device.objects.filter(
            name__iregex=r'jcy-bb|jcy-rtr'
        )
        count = matching_devices.count()

        if count > 3:
            self.logger.error(
                "Failsafe triggered: %s devices match (limit: 3). No devices updated.", count
            )
            return f"Failsafe triggered: {count} devices match (limit: 3). No devices updated."

        updated = 0
        unchanged = 0

        for device in matching_devices:
            old_tenant = device.tenant.name if device.tenant else 'None'
            old_platform = device.platform.name if device.platform else 'None'
            changes = []
            if device.tenant_id != ntc_tenant.pk:
                device.tenant = ntc_tenant
                changes.append("tenant")
            if device.platform_id != ios_platform.pk:
                device.platform = ios_platform
                changes.append("platform")
            if changes:
                device.save()
                updated += 1
                self.logger.info(
                    "Device '%s' updated: old tenant '%s', new tenant '%s'; old platform '%s', new platform '%s'",
                    device.name, old_tenant, ntc_tenant.name, old_platform, ios_platform.name
                )
            else:
                unchanged += 1
                self.logger.info(
                    "Device '%s' already set: tenant '%s', platform '%s'. No changes.",
                    device.name, old_tenant, old_platform
                )
        summary = (
            f"Processed {count} matching devices: {updated} updated, {unchanged} unchanged."
        )
        return summary

register_jobs(SetNtcTenantAndIosPlatform)