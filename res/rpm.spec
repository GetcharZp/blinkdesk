Name:       blinkdesk
Version:    1.4.9
Release:    0
Summary:    RPM package
License:    GPL-3.0
URL:        https://github.com/getcharzp/blinkdesk
Vendor:     BlinkDesk Contributors
Requires:   gtk3 libxcb libXfixes alsa-lib libva2 gstreamer1-plugins-base
Recommends: libayatana-appindicator-gtk3 libxdo

# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/

%description
The best open-source remote desktop client software, written in Rust.

%prep
# we have no source, so nothing here

%build
# we have no source, so nothing here

%global __python %{__python3}

%install
mkdir -p %{buildroot}/usr/bin/
mkdir -p %{buildroot}/usr/share/blinkdesk/
mkdir -p %{buildroot}/usr/share/blinkdesk/files/
mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps/
mkdir -p %{buildroot}/usr/share/icons/hicolor/scalable/apps/
install -m 755 $HBB/target/release/blinkdesk %{buildroot}/usr/bin/blinkdesk
install $HBB/libsciter-gtk.so %{buildroot}/usr/share/blinkdesk/libsciter-gtk.so
install $HBB/res/blinkdesk.service %{buildroot}/usr/share/blinkdesk/files/
install $HBB/res/128x128@2x.png %{buildroot}/usr/share/icons/hicolor/256x256/apps/blinkdesk.png
install $HBB/res/scalable.svg %{buildroot}/usr/share/icons/hicolor/scalable/apps/blinkdesk.svg
install $HBB/res/blinkdesk.desktop %{buildroot}/usr/share/blinkdesk/files/
install $HBB/res/blinkdesk-link.desktop %{buildroot}/usr/share/blinkdesk/files/

%files
/usr/bin/blinkdesk
/usr/share/blinkdesk/libsciter-gtk.so
/usr/share/blinkdesk/files/blinkdesk.service
/usr/share/icons/hicolor/256x256/apps/blinkdesk.png
/usr/share/icons/hicolor/scalable/apps/blinkdesk.svg
/usr/share/blinkdesk/files/blinkdesk.desktop
/usr/share/blinkdesk/files/blinkdesk-link.desktop
/usr/share/blinkdesk/files/__pycache__/*

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
    rm /usr/share/applications/blinkdesk.desktop || true
    rm /usr/share/applications/blinkdesk-link.desktop || true
    update-desktop-database
  ;;
  1)
    # for upgrade
  ;;
esac
