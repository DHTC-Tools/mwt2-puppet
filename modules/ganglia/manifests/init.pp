class ganglia::client($cluster = "mwt2", $version = '3.2.0-1') {
  package { 'ganglia-gmond': ensure => "${version}" } 
  file { 
    "/etc/ganglia/gmond.conf": 
    source => "puppet:///modules/ganglia/$cluster/gmond.conf",
    notify => Service['gmond']
  }
  service { 'gmond': 
    enable => true,
    ensure => true,
    require => Package["ganglia-gmond"],
  }
}
