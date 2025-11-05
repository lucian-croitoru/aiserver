#!/bin/bash
# =============================================================================
# Script: update_vm_gpus.sh
# Purpose: Automatically update a Unraid VM XML file with NVIDIA RTX GPUs.
#          Deletes existing hostdev blocks and inserts new ones
#          for each GPU found on the host, using the PCI addresses assigned
#          at boot. Only considers devices with VGA, NVIDIA, and RTX in lspci.
# =============================================================================

# -----------------------------
# 1. Hardcoded configuration
# -----------------------------

# Array of GPU names to search for (case-insensitive)
GPU_NAMES=("RTX 2080 Ti" "RTX 3090")

# Full path to the VM XML file to edit
VM_XML="/etc/libvirt/qemu/vmgpu1.xml"

# Folder where VBIOS/ROM files are stored
ROM_FOLDER="/mnt/user/isos/vga-bios"

# -----------------------------
# 2. Start of script
# -----------------------------
echo "==============================================="
echo "Starting GPU passthrough XML update script..."
echo "VM XML file: $VM_XML"
echo "ROM folder: $ROM_FOLDER"
echo "Supported GPU names: ${GPU_NAMES[*]}"
echo "Sleeping 10 seconds..."
sleep 10
echo "==============================================="

# -----------------------------
# 3. Remove existing <hostdev> blocks
# -----------------------------
echo "Removing existing <hostdev> blocks from VM XML..."
awk '
BEGIN {skip=0}
/<hostdev/ {skip=1}
/<\/hostdev>/ {if(skip==1){skip=0; next}}
skip==0 {print}
' "$VM_XML" > "$VM_XML.tmp" && mv "$VM_XML.tmp" "$VM_XML"
echo "Existing hostdev blocks removed."

# -----------------------------
# 4. Generate new <hostdev> blocks
# -----------------------------
echo "Generating new <hostdev> blocks for GPUs..."

HOSTDEVS=""  # This will accumulate all new hostdev XML

# Iterate over each GPU name
for GPU in "${GPU_NAMES[@]}"; do
    echo "Searching for GPU: $GPU..."

    # Filter lspci lines:
    # - must contain "VGA"
    # - must contain "NVIDIA"
    # - must contain "RTX"
    # - must match the GPU model string
    while read -r LINE; do
        PCI_ADDR=$(echo "$LINE" | awk '{print $1}')
        echo "  Found device at PCI address: $PCI_ADDR"

        # Split PCI address into bus, slot, function for XML
        IFS=':' read -r BUS SLOT_FUN <<< "$PCI_ADDR"
        IFS='.' read -r SLOT FUN <<< "$SLOT_FUN"
        XML_ADDR="domain='0x0000' bus='0x${BUS}' slot='0x${SLOT}' function='0x${FUN}'"

        # Construct the ROM file path (replace spaces with underscores)
        ROM_FILE="$ROM_FOLDER/$(echo "$GPU" | tr ' ' '_').rom"

        # Build the <hostdev> block with multifunction='on'
        HOSTDEVS+="
    <hostdev mode='subsystem' type='pci' managed='yes'>
      <driver name='vfio'/>
      <source>
        <address $XML_ADDR/>
      </source>
      <rom file='$ROM_FILE'/>
    </hostdev>"
        echo "    Added hostdev block for $GPU with ROM: $ROM_FILE"

    done < <(lspci -nn | grep -i VGA | grep -i NVIDIA | grep -i RTX | grep -i "$GPU")
done

echo "All hostdev blocks generated."

# -----------------------------
# 5. Insert new hostdev blocks into VM XML
# -----------------------------
echo "Inserting new hostdev blocks into VM XML..."

# Place the blocks just before the closing </devices> tag
awk -v newblocks="$HOSTDEVS" '
/<\/devices>/ {
    print newblocks
}
{print}
' "$VM_XML" > "$VM_XML.tmp" && mv "$VM_XML.tmp" "$VM_XML"

echo "Hostdev blocks inserted successfully."

# -----------------------------
# 6. Redefine bus addresses
# -----------------------------
echo "Redefining VM bus addresses..."
virsh define $VM_XML

# -----------------------------
# 7. Summary / Completion
# -----------------------------
echo "==============================================="
echo "GPU passthrough XML update complete!"
echo "Updated XML file: $VM_XML"
echo "VM can now be started."
echo "==============================================="
