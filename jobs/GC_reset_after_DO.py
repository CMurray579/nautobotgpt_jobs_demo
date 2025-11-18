from nautobot.apps.jobs import Job, register_jobs
from nautobot.dcim.models import Device, Platform
from nautobot.tenancy.models import Tenant
from nautobot.extras.models import Tag
from django.db import transaction

class SetTenantPlatformAndTag(Job):
    class Meta:
        name = "Set Tenant, Platform, and Tag with Failsafe"
        description = (
            "Updates tenant to 'Network to Code', platform to 'Cisco IOS', and adds 'GC_Demo_Conf' tag for devices "
            "with hostname containing 'jcy-bb' or 'jcy-rtr' (case-insensitive). Aborts if more than 3 devices match."
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

        # Retrieve or create the required tag
        gc_demo_tag, created = Tag.objects.get_or_create(name="GC_Demo_Conf")
        if created:
            self.logger.info("Created missing tag 'GC_Demo_Conf'.")

        # Find matching devices
        matching_devices = Device.objects.filter(name__iregex=r'jcy-bb|jcy-rtr')
        count = matching_devices.count()

        if count > 3:
            self.logger.error(
                "Failsafe triggered: %s devices match (limit: 3). No devices updated.", count
            )
            return f"Failsafe triggered: {count} devices match (limit: 3). No devices updated."

        updated = 0
        unchanged = 0

        with transaction.atomic():
            for device in matching_devices:
                changed = False
                old_tenant = device.tenant.name if device.tenant else 'None'
                old_platform = device.platform.name if device.platform else 'None'
                tags_before = [t.name for t in device.tags.all()]
                changes = []

                # Update Tenant
                if device.tenant_id != ntc_tenant.pk:
                    device.tenant = ntc_tenant
                    changed = True
                    changes.append("tenant")

                # Update Platform
                if device.platform_id != ios_platform.pk:
                    device.platform = ios_platform
                    changed = True
                    changes.append("platform")

                # Add Tag if missing
                if not device.tags.filter(pk=gc_demo_tag.pk).exists():
                    # Use set() to avoid duplicates
                    device.tags.add(gc_demo_tag)
                    changed = True
                    changes.append("tag")

                if changed:
                    device.save()
                    updated += 1
                    self.logger.info(
                        "Device '%s' updated: tenant '%s'→'%s'; platform '%s'→'%s'; tags %s→%s",
                        device.name, old_tenant, ntc_tenant.name, old_platform, ios_platform.name, tags_before, [t.name for t in device.tags.all()]
                    )
                else:
                    unchanged += 1
                    self.logger.info(
                        "Device '%s' was already set: tenant '%s', platform '%s', tags %s. No changes.",
                        device.name, old_tenant, old_platform, tags_before
                    )
        summary = (
            f"Processed {count} matching devices: {updated} updated, {unchanged} unchanged."
        )
        return summary

register_jobs(SetTenantPlatformAndTag)