
Name:           cinnamon-clipboard
Version:        1.0.4
Release:        1%{?dist}
Summary:        Clipboard manager for Cinnamon and Linux desktops

License:        GPL-3.0-or-later
URL:            https://github.com/Vaider13/cinnamon-clipboard
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  desktop-file-utils
BuildRequires:  gettext
BuildRequires:  python3-devel

Requires:       python3
Requires:       python3-gobject
Requires:       gtk3
Requires:       xapps
Requires:       keybinder3
Requires:       python3-setproctitle
Requires:       python3-xlib

%description
A simple, lightweight clipboard manager with GTK3, SQLite persistence,
keyboard shortcuts, and privacy filtering for password managers.

%prep
%autosetup -n %{name}-%{version}

%build
for po_file in locale/*/LC_MESSAGES/cinnamon-clipboard.po; do
    [ -f "$po_file" ] || continue
    msgfmt "$po_file" -o "${po_file%.po}.mo"
done

%install
rm -rf %{buildroot}

install -d %{buildroot}%{python3_sitelib}/cinnamon_clipboard
cp -a src/cinnamon_clipboard/. \
    %{buildroot}%{python3_sitelib}/cinnamon_clipboard/

find %{buildroot}%{python3_sitelib}/cinnamon_clipboard \
    -type d -name __pycache__ -prune -exec rm -rf {} +
find %{buildroot}%{python3_sitelib}/cinnamon_clipboard \
    -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

install -D -m 0755 /dev/stdin \
    %{buildroot}%{_bindir}/cinnamon-clipboard <<'EOF'
#!/bin/sh
exec python3 -m cinnamon_clipboard.app "$@"
EOF

install -D -m 0644 data/icons/cinnamon-clipboard.png \
    %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/cinnamon-clipboard.png

install -d %{buildroot}%{_datadir}/applications

cat > %{_builddir}/cinnamon-clipboard.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Cinnamon Clipboard
Name[es]=Portapapeles de Cinnamon
Name[it]=Appunti di Cinnamon
Name[fr]=Presse-papiers de Cinnamon
Name[de]=Cinnamon-Zwischenablage
Name[ru]=Буфер обмена Cinnamon
Name[ja]=Cinnamon クリップボード
Comment=Clipboard manager for Cinnamon
Comment[es]=Gestor de portapapeles para Cinnamon
Comment[it]=Gestore degli appunti per Cinnamon
Comment[pt_BR]=Gerenciador da área de transferência para Cinnamon
Comment[fr]=Gestionnaire de presse-papiers pour Cinnamon
Comment[de]=Zwischenablageverwaltung für Cinnamon
Comment[ru]=Менеджер буфера обмена для Cinnamon
Comment[ja]=Cinnamon 用クリップボードマネージャー
Exec=cinnamon-clipboard
Icon=cinnamon-clipboard
StartupWMClass=CinnamonClipboard
Terminal=false
Categories=Utility;GTK;
EOF

desktop-file-install \
    --dir=%{buildroot}%{_datadir}/applications \
    %{_builddir}/cinnamon-clipboard.desktop

for mo_file in locale/*/LC_MESSAGES/cinnamon-clipboard.mo; do
    [ -f "$mo_file" ] || continue
    lang=$(basename "$(dirname "$(dirname "$mo_file")")")
    install -D -m 0644 "$mo_file" \
        "%{buildroot}%{_datadir}/locale/$lang/LC_MESSAGES/cinnamon-clipboard.mo"
done

%find_lang %{name}

%files -f %{name}.lang
%license LICENSE
%doc README.md
%{_bindir}/cinnamon-clipboard
%{python3_sitelib}/cinnamon_clipboard/
%{_datadir}/applications/cinnamon-clipboard.desktop
%{_datadir}/icons/hicolor/512x512/apps/cinnamon-clipboard.png

%changelog
* Thu Oct 22 2026 Pablo <quircopablo@gmail.com> - 1.0.4-1
- Initial RPM packaging for Fedora