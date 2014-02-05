if [ $1 -eq 1 ]; then
	# first install
	/usr/sbin/useradd -r -s /sbin/nologin -d %{_sysconfdir}/rockpack/mainsite %{name} 2>/dev/null
	cat >/etc/sysconfig/dolly-mainsite <-EOF
		ROCKPACK_SETTINGS=/etc/rockpack/mainsite/dolly-config.py
		CFG=/etc/rockpack/mainsite/uwsgi.ini:dolly
	EOF
	ln -s rockpack-mainsite /etc/rc.d/init.d/dolly-mainsite
	/sbin/chkconfig --add rockpack-mainsite
	/sbin/chkconfig --add dolly-mainsite
fi
