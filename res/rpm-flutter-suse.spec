Name:       blinkdesk
Version:    1.4.9
Release:    0
Summary:    RPM package
License:    GPL-3.0
URL:        https://github.com/getcharzp/blinkdesk
Vendor:     BlinkDesk Contributors
Requires:   gtk3 libxcb1 libXfixes3 alsa-utils libXtst6 libva2 gstreamer-plugins-base gstreamer-plugin-pipewire
Recommends: libayatana-appindicator3-1 xdotool
Provides:   libdesktop_drop_plugin.so()(64bit), libdesktop_multi_window_plugin.so()(64bit), libfile_selector_linux_plugin.so()(64bit), libflutter_custom_cursor_plugin.so()(64bit), libflutter_linux_gtk.so()(64bit), libscreen_retriever_plugin.so()(64bit), libtray_manager_plugin.so()(64bit), liburl_launcher_linux_plugin.so()(64bit), libwindow_manager_plugin.so()(64bit), libwindow_size_plugin.so()(64bit), libtexture_rgba_renderer_plugin.so()(64bit)

# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/

%description
The best open-source remote desktop client software, written in Rust.

%prep
# we have no source, so nothing here

%build
# we have no source, so nothing here

# %global __python %{__python3}

%install

mkdir -p "%{buildroot}/usr/share/blinkdesk" && cp -r ${HBB}/flutter/build/linux/x64/release/bundle/* -t "%{buildroot}/usr/share/blinkdesk"
mkdir -p "%{buildroot}/usr/bin"
install -Dm 644 $HBB/res/blinkdesk.service -t "%{buildroot}/usr/share/blinkdesk/files"
install -Dm 644 $HBB/res/blinkdesk.desktop -t "%{buildroot}/usr/share/blinkdesk/files"
install -Dm 644 $HBB/res/blinkdesk-link.desktop -t "%{buildroot}/usr/share/blinkdesk/files"
install -Dm 644 $HBB/res/128x128@2x.png "%{buildroot}/usr/share/icons/hicolor/256x256/apps/blinkdesk.png"
install -Dm 644 $HBB/res/scalable.svg "%{buildroot}/usr/share/icons/hicolor/scalable/apps/blinkdesk.svg"

%files
/usr/share/blinkdesk/*
/usr/share/blinkdesk/files/blinkdesk.service
/usr/share/icons/hicolor/256x256/apps/blinkdesk.png
/usr/share/icons/hicolor/scalable/apps/blinkdesk.svg
/usr/share/blinkdesk/files/blinkdesk.desktop
/usr/share/blinkdesk/files/blinkdesk-link.desktop

%changelog
# let's skip this for now

%pre
# can do something for centos7
case "$1" in
  1)
    # for install
  ;;
  2)
    # for upgrade
    systemctl stop blinkdesk || true
  ;;
esac

%post
cp /usr/share/blinkdesk/files/blinkdesk.service /etc/systemd/system/blinkdesk.service
cp /usr/share/blinkdesk/files/blinkdesk.desktop /usr/share/applications/
cp /usr/share/blinkdesk/files/blinkdesk-link.desktop /usr/share/applications/
ln -sf /usr/share/blinkdesk/blinkdesk /usr/bin/blinkdesk
systemctl daemon-reload
systemctl enable blinkdesk
systemctl start blinkdesk
update-desktop-database

%preun
case "$1" in
  0)
    # for uninstall
    systemctl stop blinkdesk || true
    systemctl disable blinkdesk || true
    rm /etc/systemd/system/blinkdesk.service || true
  ;;
  1)
    # for upgrade
  ;;
esac

%postun
case "$1" in
  0)
    # for uninstall
    rm /usr/bin/blinkdesk || true
    rmdir /usr/lib/blinkdesk || true
    rmdir /usr/local/blinkdesk || true
    rmdir /usr/share/blinkdesk || true
    rm /usr/share/applications/blinkdesk.desktop || true
    rm /usr/share/applications/blinkdesk-link.desktop || true
    update-desktop-database
  ;;
  1)
    # for upgrade
    rmdir /usr/lib/blinkdesk || true
    rmdir /usr/local/blinkdesk || true
  ;;
esac
