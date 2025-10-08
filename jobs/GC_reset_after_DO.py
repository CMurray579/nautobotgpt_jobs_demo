from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import Device
from nautobot.tenancy.models import Tenant

class SetNtcTenantOnJcyDevices(Job):
    class Meta:
        name = "Set 'Network to Code' Tenant with Failsafe"
        description = (
            "Sets the tenant to 'Network to Code' for devices whose hostname contains 'jcy-bb' or 'jcy-rtr' "
            " (case-insensitive), but aborts if more than 3 devices match."
        )

    def run(self):
        try:
            ntc_tenant = Tenant.objects.get(name__iexact="Network to Code")
        except Tenant.DoesNotExist:
            self.logger.error("Tenant 'Network to Code' does not exist. Please create it first.")
            return "Tenant 'Network to Code' not found, job aborted."

        matching_devices = Device.objects.filter(
            name__iregex=r'jcy-bb|jcy-rtr'
        )

        count = matching_devices.count()

        if count > 3:
            self.logger.error(
                "Failsafe triggered: %s devices match (limit: 3). No tenants updated.",
                count
            )
            return f"Failsafe triggered: {count} devices match (limit: 3). No tenants updated."

        updated = 0
        unchanged = 0

        for device in matching_devices:
            if device.tenant_id != ntc_tenant.pk:
                old_tenant = device.tenant.name if device.tenant else 'None'
                device.tenant = ntc_tenant
                device.save()
                updated += 1
                self.logger.info(
                    "Device '%s' tenant set from '%s' to 'Network to Code'", device.name, old_tenant
                )
            else:
                unchanged += 1
                self.logger.info(
                    "Device '%s' already has tenant 'Network to Code', no action taken", device.name
                )
        summary = (
            f"Processed {count} matching devices: {updated} updated, {unchanged} unchanged."
        )
        return summary

register_jobs(SetNtcTenantOnJcyDevices)