from nautobot.apps.jobs import register_jobs
from .hello_world import HelloWorldJob
from .device_uptime_checker import DeviceUptimeCheck
from .interface_description_search_alpha import InterfaceDescriptionSearch
from .IPv4_check_Clive import DevicesRequirePrimaryIPv4
from .unused_interfaces import UnusedInterfacesReport
from .replace_mgmt_address import SubstituteIPWithMgmt
from .object_interaction import UpdateDeviceSerial
from .update_interface_description import UpdateIntDescription
from .GC_reset_after_DO import SetNtcTenantOnJcyDevices
from .reset_configs_GC import EnableHttpServicesOnTaggedDevices

name = "Tutorial Jobs" 

register_jobs(
	HelloWorldJob,
	DeviceUptimeCheck,
	InterfaceDescriptionSearch,
	DevicesRequirePrimaryIPv4, 
	UnusedInterfacesReport,
	SubstituteIPWithMgmt,
	UpdateDeviceSerial,
	UpdateIntDescription,
	SetNtcTenantOnJcyDevices,
	EnableHttpServicesOnTaggedDevices
	)