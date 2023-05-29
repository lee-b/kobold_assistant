#!/bin/sh

pactl load-module module-null-sink sink_name=kobold-assistant-virtual-mic-sink sink_properties=device.description=KoboldAssistantVirtualMicSink
pactl load-module module-remap-source master=kobold-assistant-virtual-mic-sink.monitor source_name=audiorelay-virtual-mic-sink source_properties=device.description=Virtual-Mic
pactl load-module module-null-sink sink_name=kobold-assistant-virtual-speakers sink_properties=device.description=KoboldAssistantVirtualSpeakers


