class mwt2::worker {
  # The regular expression checks only for EL major release version 
  case $::operatingsystemrelease {
    /^5\.[0-9]$/ : {}
    /^6\.[0-9]$/ : {}
  }
  # Gets rid of default yum repos that aren't managed by Cobbler
  #  and turns off automatic updates.
  package {'yum-autoupdate': ensure => absent }
  file { '/etc/cron.d/yum.cron': ensure => absent }
  file { '/etc/cron.daily/yum.cron': ensure => absent }
  file { "/etc/yum.repos.d/sl.repo": ensure => absent }
  file { "/etc/yum.repos.d/sl-other.repo": ensure => absent }
  file { "/etc/yum.repos.d/epel.repo": ensure => absent }
  file { "/etc/yum.repos.d/epel-testing.repo": ensure => absent }
 
  # Get rid of some random makewhatisdb, locatedb..  
  file { "/etc/cron.daily/makewhatis.cron": ensure => absent }
  file { "/etc/cron.daily/mlocate.cron": ensure => absent }

  # Lets turn on smartd monitoring
  service { "smartd" : enable => true, ensure => true}
 
  # Turn off sysstat
  #service { "sysstat" : enable => false, ensure => false}

  # Turn off firewall
  service { "iptables" : enable => false, ensure => false}
  service { "ip6tables": enable => false, ensure => false}

  # Turn off kdump
  service { "kdump" : enable => false, ensure => false}

  # Let's make a symlink from python to python26
  file { '/usr/bin/python26' : 
    ensure => link,
    target => '/usr/bin/python',
  }

  # LSM
  file { "/usr/local/bin/lsm-get":
    source => "puppet:///modules/mwt2/lsm-get",
    owner  => root,
    group  => root,
  }
  file { "/usr/local/bin/lsm-put":
    source => "puppet:///modules/mwt2/lsm-put",
    owner  => root,
    group  => root,
  }
  file { "/usr/local/bin/lsm-rm": 
    source => "puppet:///modules/mwt2/lsm-rm",
    owner  => root,
    group  => root,
  }
  file { "/usr/local/bin/lsm-df":
    source => "puppet:///modules/mwt2/lsm-df",
    owner  => root,
    group  => root,
  }
  file { "/usr/local/bin/timed_command.py": 
    source => "puppet:///modules/mwt2/timed_command.py",
    owner  => root,
    group  => root,
  }
  file { "/usr/local/bin/lsm.py": 
    source => "puppet:///modules/mwt2/lsm.py",
    owner  => root,
    group  => root,
  }
  file { "/var/log/lsm": ensure => directory, mode => 0777 }

  # pcache 
  file { "/usr/local/bin/pcache.py":
    source => "puppet:///modules/mwt2/pcache.py",
    owner  => root,
    group  => root,
  } 

  # Scratch space
  file { "/scratch":
    ensure => directory,
    mode   => 1777
  }
}
