if [ $1 -eq 1 ]; then
	# first install
	/usr/sbin/useradd -r -s /sbin/nologin -d %{_sysconfdir}/%{name} %{name} 2>/dev/null
	/sbin/chkconfig --add %{name}
fi
