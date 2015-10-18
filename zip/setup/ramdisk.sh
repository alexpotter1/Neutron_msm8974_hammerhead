#!/sbin/sh

mkdir /tmp/ramdisk
cp /tmp/boot.img-ramdisk.gz /tmp/ramdisk/
cd /tmp/ramdisk/
gunzip -c /tmp/ramdisk/boot.img-ramdisk.gz | cpio -i
rm /tmp/boot.img-ramdisk.gz
rm /tmp/ramdisk/boot.img-ramdisk.gz
rm /tmp/ramdisk/fstab.hammerhead
rm /tmp/ramdisk/init.hammerhead.rc
cp /tmp/init.neutron.rc /tmp/ramdisk/
cp /tmp/fstab.hammerhead /tmp/ramdisk/
cp /tmp/init.hammerhead.rc /tmp/ramdisk/
chmod 750 /tmp/ramdisk/init.neutron.rc
chmod 640 /tmp/ramdisk/fstab.hammerhead
chmod 750 /tmp/ramdisk/init.hammerhead.rc
find . | cpio -o -H newc | gzip > /tmp/boot.img-ramdisk.gz
rm -r /tmp/ramdisk
