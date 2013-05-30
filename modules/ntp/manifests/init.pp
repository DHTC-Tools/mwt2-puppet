class ntp::client {
  package { 'ntp': ensure => present }

  file { "/etc/ntp.conf":        
    source  => "puppet:///modules/ntp/ntp.conf.${::domain}", 
    owner   => "root",
    group   => "root",
  }
  file { "/etc/sysconfig/clock": 
    source  => "puppet:///modules/ntp/clock",
    owner   => "root",
    group   => "root",
  }
  file { "/etc/sysconfig/ntpd":  
    source  => "puppet:///modules/ntp/ntpd",
    owner   => "root",
    group   => "root",
  }
  file { "/etc/localtime":
    source  => "puppet:///modules/ntp/localtime",
    owner   => "root",
    group   => "root",
  }

  exec { "/bin/mv /dev/rtc /dev/rtc-old": creates => "/dev/rtc-old" }

  file { "/dev/rtc":
    ensure  => "/dev/rtc0",
    force   => true,
    require => Exec["/bin/mv /dev/rtc /dev/rtc-old"],
    notify  => Service['ntpd']
  }

  service { "ntpd":
    enable    => true,
    ensure    => true,
    require   => Package["ntp"],
    subscribe => [
      File["/etc/sysconfig/clock"],
      File["/etc/ntp.conf"],
      File["/etc/sysconfig/ntpd"],
      File["/etc/localtime"] ]
  }
}
