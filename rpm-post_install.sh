/usr/sbin/useradd -r -s /sbin/nologin -d %{_sysconfdir}/%{name} %{name} 2>/dev/null
/sbin/chkconfig --add %{name}
