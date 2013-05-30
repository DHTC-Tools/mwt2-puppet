#########################################################################
#
# Installs Condor and the various dependencies
#
#
#    condor::install { "${::hostname}" : version => '7.8.6-73238',
#                                        start   => true }
#
#########################################################################

define condor::install (

   $version    = '7.8.8-110288',
   $start      = true

) {

  # Ensure that the requested condor version is installed on the node

  package { 'condor' : 
    ensure     => "${version}"
  }


  # Install the master configuration file consistent with the version of condor

  file { '/etc/condor/condor_config' :
    ensure     => present,
    owner      => 'root',
    group      => 'root',
    mode       => '0644',
    require    => Package['condor'],
    source     => "puppet:///modules/condor/mwt2/condor_config.${version}"
  }


  # Put out our version the "local" which should be empty (but must exist)

  file { '/etc/condor/condor_config.local' :
    ensure     => present,
    owner      => 'root',
    group      => 'root',
    mode       => '0644',
    require    => Package['condor'],
    source     => "puppet:///modules/condor/mwt2/condor_config.local"
  }


  # Make certain the configuration directory exists and is empty

  file { [ "/etc/condor/config.d" ] :
    ensure     => directory,
    recurse    => true,
    purge      => true
  }


  # Startup the condor services, but only if all needed files exist

  service { 'condor' :
    hasrestart => true,
    enable     => $start,
    ensure     => $start,
    require    => [ Package["condor"],
                    File["/etc/condor/condor_config"],
                    File["/etc/condor/condor_config.local"] ,
                    File["/usr/bin/condor_nfslite_job_wrapper.sh"],
                    File["/usr/local/sbin/condor_node_check.sh"],
                  ],
    subscribe  => [ File["/etc/condor/condor_config"],
                    File["/etc/condor/condor_config.local"] 
                  ],
    restart    => "/usr/sbin/condor_reconfig",
  }


  # Condor installs libvirtd, which we do not want to use

  service { 'libvirtd' :
    enable     => false,
    ensure     => false
  }

}


#########################################################################
#
# Installs the base Condcr configuration files common to all nodes
#
#
#    condor::install::base { "${::hostname}" : pool => 'uc' }
#
#########################################################################


define condor::install::base (

  $pool = ''

) {

  # Install the configuration file defining the pool we participate in

  case $pool {
    'uc'         : { condor::conf { 'pool' : conf => '00-pool.conf', conf_src => '00-pool.conf.uc'         } }
    'iu'         : { condor::conf { 'pool' : conf => '00-pool.conf', conf_src => '00-pool.conf.iu'         } }
    'uiuc'       : { condor::conf { 'pool' : conf => '00-pool.conf', conf_src => '00-pool.conf.uiuc'       } }
    'validation' : { condor::conf { 'pool' : conf => '00-pool.conf', conf_src => '00-pool.conf.validation' } }
    default      : { notify { "Unknown pool specified : $pool" : } }
  }


  # Install the common set of configurations

  condor::conf { 'common' : conf => '01-common.conf' }

}


#########################################################################
#
# Installs the Condcr configuration files for a Gatekeeper Node
#
#
#    condor::node::gatekeeper { "${::hostname}" : pool => 'uc' }
#
#########################################################################

define condor::node::gatekeeper (

  $pool = ''

) {

  # Install the base set of configuration files in the given pool

  condor::install::base { 'gatekeeper' : pool => $pool }


  # The common set of configuration files needed to make a Gatekeeper work

  condor::conf { 'common-gatekeeper' : conf     => '02-common-gatekeeper.conf' }
  condor::conf { 'job'               : conf     => '50-job.conf'               }
  condor::conf { 's_p_r'             : conf     => '55-s_p_r.conf'             }
  condor::conf { 'gratia'            : conf     => '99-gratia.conf'            }


  # The pool specific Gatekeeper configuration files

  case $pool {
    'uc'         : { condor::conf { 'gatekeeper' : conf => '03-gatekeeper.conf', conf_src => '03-gatekeeper.conf.uc'         } }
    'iu'         : { condor::conf { 'gatekeeper' : conf => '03-gatekeeper.conf', conf_src => '03-gatekeeper.conf.iu'         } }
    'uiuc'       : { condor::conf { 'gatekeeper' : conf => '03-gatekeeper.conf', conf_src => '03-gatekeeper.conf.uiuc'       } }
    'validation' : { condor::conf { 'gatekeeper' : conf => '03-gatekeeper.conf', conf_src => '03-gatekeeper.conf.validation' } }
    default      : { notify { "Unknown pool specified : $pool" : } }
  }


  # The pool specific Flocking configuration files

  case $pool {
    'uc'         : { condor::conf { 'flocking' : conf => '20-flocking.conf', conf_src => '20-flocking.conf.uc'         } }
    'iu'         : { condor::conf { 'flocking' : conf => '20-flocking.conf', conf_src => '20-flocking.conf.iu'         } }
    'uiuc'       : { condor::conf { 'flocking' : conf => '20-flocking.conf', conf_src => '20-flocking.conf.uiuc'       } }
    'validation' : { condor::conf { 'flocking' : conf => '20-flocking.conf', conf_src => '20-flocking.conf.validation' } }
    default      : { notify { "Unknown pool specified : $pool" : } }
  }

}


#########################################################################
#
# Installs the Condcr configuration files for a Condor Head Node
#
#
#    condor::node::head { "${::hostname}" : pool => 'uc' }
#
#########################################################################

define condor::node::head (

  $pool = ''

) {

  # Install the base set of configuration files in the given pool

  condor::install::base { 'head' : pool => $pool }


  # The common set of configuration files needed to make a Condor head node

  condor::conf { 'common-head' : conf => '02-common-head.conf' }
  condor::conf { 'job'         : conf => '50-job.conf'         }


  # The pool specific Head node configuration files

  case $pool {
    'uc'         : { condor::conf { 'head'  : conf => '03-head.conf' , conf_src => '03-head.conf.uc'         } }
    'iu'         : { condor::conf { 'head'  : conf => '03-head.conf' , conf_src => '03-head.conf.iu'         } }
    'uiuc'       : { condor::conf { 'head'  : conf => '03-head.conf' , conf_src => '03-head.conf.uiuc'       } }
    'validation' : { condor::conf { 'head'  : conf => '03-head.conf' , conf_src => '03-head.conf.validation' } }
    default      : { notify { "Unknown pool specified : $pool" : } }
  }


  # The pool specific group accounting

  case $pool {
    'uc'         : { condor::conf { 'group' : conf => '10-group.conf', conf_src => '10-group.conf.uc'         } }
    'iu'         : { condor::conf { 'group' : conf => '10-group.conf', conf_src => '10-group.conf.iu'         } }
    'uiuc'       : { condor::conf { 'group' : conf => '10-group.conf', conf_src => '10-group.conf.uiuc'       } }
    'validation' : { condor::conf { 'group' : conf => '10-group.conf', conf_src => '10-group.conf.validation' } }
    default      : { notify { "Unknown pool specified : $pool" : } }
  }


  # The pool specific Flocking configuration files

  case $pool {
    'uc'         : { condor::conf { 'flocking' : conf => '20-flocking.conf', conf_src => '20-flocking.conf.uc'         } }
    'iu'         : { condor::conf { 'flocking' : conf => '20-flocking.conf', conf_src => '20-flocking.conf.iu'         } }
    'uiuc'       : { condor::conf { 'flocking' : conf => '20-flocking.conf', conf_src => '20-flocking.conf.uiuc'       } }
    'validation' : { condor::conf { 'flocking' : conf => '20-flocking.conf', conf_src => '20-flocking.conf.validation' } }
    default      : { notify { "Unknown pool specified : $pool" : } }
  }

}


#########################################################################
#
# Installs the Condcr configuration files for a Condor Management Node
#
#
#    condor::node::head { "${::hostname}" : pool => 'uc' }
#
#########################################################################

define condor::node::management (

  $pool = ''

) {


  # Install the base set of configuration files in the given pool

  condor::install::base { 'cnode' : pool => $pool }


  # The common set of configuration files needed to make a Condor Management node

  condor::conf { 'common-management' : conf => '02-common-management.conf' }


  # The pool specific Management node configuration files

  case $pool {
    'uc'         : { condor::conf { 'management'  : conf => '03-management.conf' , conf_src => '03-management.conf.uc'         } }
    'iu'         : { condor::conf { 'management'  : conf => '03-management.conf' , conf_src => '03-management.conf.iu'         } }
    'uiuc'       : { condor::conf { 'management'  : conf => '03-management.conf' , conf_src => '03-management.conf.uiuc'       } }
    'validation' : { condor::conf { 'management'  : conf => '03-management.conf' , conf_src => '03-management.conf.validation' } }
    default      : { notify { "Unknown pool specified : $pool" : } }
  }

}


#########################################################################
#
# Installs the Condcr configuration files for a Condor C Node
#
#
#    condor::node::head { "${::hostname}" : pool => 'uc',
#                                           core => 'score' }
#
#########################################################################

define condor::node::cnode (

  $pool = '',
  $core = 'score'

) {


  # Install the base set of configuration files in the given pool

  condor::install::base { 'cnode' : pool => $pool }


  # The common set of configuration files needed to make a C node

  condor::conf { 'common-cnode' : conf => '02-common-cnode.conf', conf_src => '02-common-cnode.conf' }
  condor::conf { 'cron'         : conf => '30-cron.conf'}
  condor::conf { 'job'          : conf => '50-job.conf' }
#  condor::conf { 'uc3'          : conf => '80-uc3.conf' }


  # The pool specific C node configuration files

  case $pool {
    'uc'         : { condor::conf { 'cnode' : conf => '03-cnode.conf', conf_src => '03-cnode.conf.uc'         } }
    'iu'         : { condor::conf { 'cnode' : conf => '03-cnode.conf', conf_src => '03-cnode.conf.iu'         } }
    'uiuc'       : { condor::conf { 'cnode' : conf => '03-cnode.conf', conf_src => '03-cnode.conf.uiuc'       } }
    'validation' : { condor::conf { 'cnode' : conf => '03-cnode.conf', conf_src => '03-cnode.conf.validation' } }
    default      : { notify { "Unknown pool specified : $pool" : } }
  }


  # The core specific C node configuration files

  case $core {
    'score'  : { }
    'mcore1' : { condor::conf { 'core' : conf => '70-mcore.conf', conf_src => '70-mcore1.conf' } }
    'mcore2' : { condor::conf { 'core' : conf => '70-mcore.conf', conf_src => '70-mcore2.conf' } }
    'mcore3' : { condor::conf { 'core' : conf => '70-mcore.conf', conf_src => '70-mcore3.conf' } }
    default  : { notify { "Unknown core speificed : $core" : } }
  }


}

#########################################################################
##
## Installs a given configuration file from the mwt2 configuration
##
##    condor::conf { 'conf-name' : conf      => '01-common.conf',
##                                 conf_src  => '' }
##
#########################################################################

define condor::conf (

  $conf     = '',
  $conf_src = ''

) {

  # If only the destination was given, use it as the source

  if $conf_src == ''
    { $src = "${conf}" }
  else
    { $src = "${conf_src}" }


  # Install the given file

  file { [ "/etc/condor/config.d/${conf}" ]:
    ensure     => present,
    owner      => 'root',
    group      => 'root',
    mode       => '0644',
    source     => "puppet:///modules/condor/mwt2/${src}",
    require    => Package['condor']
  }

}


#########################################################################
##
## Configures a C-Node to run only validation jobs
##
#########################################################################

define condor::conf::onlyvalidation {

  condor::conf { 'onlyvalidation' : conf => '05-onlyvalidation.conf' }

}
