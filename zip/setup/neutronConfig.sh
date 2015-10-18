#!/sbin/sh

if [ ! -e /system/etc/init.d ]; then
  mkdir /system/etc/init.d
  chown -R root.root /system/etc/init.d
  chmod -R 755 /system/etc/init.d
fi;

if [ ! -e /system/su.d ]; then
  mkdir /system/su.d
  chown -R root.root /system/su.d
  chmod -R 700 /system/su.d
fi;
