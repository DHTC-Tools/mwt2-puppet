class dell::tools($version) {
  package { "dell-omsa-repository-2-5": ensure => absent }
  package { "firmware-tools": ensure => present }
  package { "check_openmanage": ensure => absent }
  package { "srvadmin-all": ensure => "${version}" }
  package { "delldset.x86_64": ensure => present, require => Package["srvadmin-all"] }
  package { "nagios-plugins-openmanage.x86_64": ensure => present }
  service { ["dsm_om_connsvc", "dsm_om_shrsvc"]:
    enable => true,
    ensure => true,
    require => Package ["srvadmin-all"]
  }
}
