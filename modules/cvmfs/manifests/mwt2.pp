#########################################################################
#
# Installs CVMFS Client and the various dependencies
#
#
#    cvmfs::install { "${::hostname}": version=>'2.0.19-1.el6' }
#
#########################################################################

define cvmfs::install (

  $version = '2.0.19-1.el6',
  $site    = 'uc'

) 

{

  file { 'RPM-GPG-KEY-CernVM' : 
    path       => "/etc/pki/rpm-gpg/RPM-GPG-KEY-CernVM",
    source     => "puppet:///modules/cvmfs/mwt2/RPM-GPG-KEY-CernVM" 
  }

  package { 'fuse.x86_64' :
    ensure     => present
  }

  file { "/etc/fuse.conf" :
    source     => "puppet:///modules/cvmfs/mwt2/fuse.conf",
    require    => Package['fuse.x86_64']
  }

#  file { "/etc/sysconfig/modules/fuse.modules" :
#    source     => "puppet:///modules/cvmfs/mwt2/fuse.modules",
#    require    => Package['fuse.x86_64'],
#    mode       => 0755
#  }

#  exec { "/etc/sysconfig/modules/fuse.modules" : 
#    onlyif     => "/bin/sh -c '! lsmod | grep -q fuse'", 
#    require    => File["/etc/sysconfig/modules/mwt2/fuse.modules"], 
#    notify     => Service['autofs'] 
#  }

  package { 'autofs.x86_64' :
    ensure     => present
  }

  service { "autofs" :
    enable     => true,
    ensure     => true,
    pattern    => "automount",
    require    => Package['autofs.x86_64'] 
  }

  file { "/etc/auto.master" :
    owner      => "root",
    group      => "root",
    mode       => 644,
    source     => "puppet:///modules/cvmfs/mwt2/auto.master",
    require    => Package['autofs.x86_64'],
    notify     => [Service['autofs']]
  }

  package { 'cvmfs-keys' :         
    ensure     => present,
    require    => File['RPM-GPG-KEY-CernVM']
  }

  package { 'cvmfs' :            
    ensure     => "${version}",
    require    => [
      File['RPM-GPG-KEY-CernVM'],
      Package['fuse.x86_64'],
      Package['autofs.x86_64'],
      Package['cvmfs-keys'] 
    ]
  }

  package { 'cvmfs-init-scripts' : 
    ensure     => present,
    require    => Package['cvmfs'] 
  }

  file { "/etc/cvmfs/default.local" :
    owner      => "root",
    group      => "root",
    mode       => 644,
    notify     => [Service["cvmfs"], Service["autofs"]],
    require    => Package['cvmfs'],
    source     => "puppet:///modules/cvmfs/mwt2/default.local.${site}"
  }

  file { '/scratch/cvmfs' :
    ensure     => directory,
    owner      => "cvmfs",
    group      => "cvmfs"
  }


  cvmfs::repository::cern { 'atlas.cern.ch'           : }   
  cvmfs::repository::cern { 'atlas-nightlies.cern.ch' : }  
  cvmfs::repository::cern { 'atlas-condb.cern.ch'     : }  
  cvmfs::repository::cern { 'sft.cern.ch'             : }  
  cvmfs::repository::mwt2 { 'osg.mwt2.org'            : }  


  service { 'cvmfs' :
    enable     => true,
    ensure     => true,
    hasstatus  => true,
    hasrestart => true,
    restart    => "/etc/init.d/cvmfs reload",
    require    => [ 
      Package['cvmfs'], 
      Package['cvmfs-init-scripts'], 
      Package['cvmfs-keys'],
      Service['autofs'],
      File['/etc/cvmfs/default.local'], 
      File['/etc/auto.master'], 
      File['/etc/fuse.conf']  
    ]
  }


# The cvmfs_reload is used to force a "reload" of the CVMFS configuration once per day

  file { "/etc/cron.d/cvmfs_reload.cron":
    owner      => "root",
    group      => "root",
    mode       => 644,
    source     => "puppet:///modules/cvmfs/mwt2/cvmfs_reload.cron",
    require    => Package['cvmfs']
  }

}


#########################################################################
#
# Creates the home area for the given usatlas VO user
#
#    cvmfs::mkhome::usatlas { 'usatlas1' : }
#
#########################################################################

define cvmfs::mkhome::usatlas {

  file { "/home/usatlas/${name}" :
    ensure     => directory,
    owner      => "${name}",
    group      => "usatlas",
    mode       => 700
  }

}


#########################################################################
#
# Creates the appropriate 'local' configuration file for a cern repository
#
#    cvmfs::repository::cern { 'atlas.cern.ch' : }   
#
#########################################################################

define cvmfs::repository::cern { 

  file { "/etc/cvmfs/config.d/${name}.local" :
    owner      => "root",
    group      => "root",
    mode       => 644,
    notify     => [Service["cvmfs"], Service["autofs"]],
    source     => "puppet:///modules/cvmfs/mwt2/${name}.local",
    require    => Package['cvmfs']
  }

  exec { "probe ${ name }" :
    command    => "/etc/init.d/cvmfs probe",
    creates    => "/cvmfs/${name}",
    require    => Service['cvmfs']  
  }

}


#########################################################################
#
# Creates the appropriate 'local' configuration file for a given repository
#
#    cvmfs::repository::mwt2 { "${::hostname}" : site       => 'uc',
#                                                repository => 'osg.mwt2.org' }
#
#########################################################################

define cvmfs::repository::mwt2 (               

   $site         = 'uc',
   $repository   = 'osg.mwt2.org'

) {

   file { "/etc/cvmfs/config.d/${repository}.conf" :
     owner     => "root",
     group     => "root",
     mode      => 644,
     notify    => [Service["cvmfs"], Service["autofs"]],
     source    => "puppet:///modules/cvmfs/mwt2/${repository}.conf.${site}",
     require   => Package['cvmfs']
   }

   file { "/etc/cvmfs/keys/${repository}.pub" :
     path      => "/etc/cvmfs/keys/${repository}.pub",
     owner     => "root",
     group     => "root",
     mode      => 444,
     source    => "puppet:///modules/cvmfs/mwt2/${repository}.pub",
     notify    => [Service["cvmfs"], Service["autofs"]],
     require   => Package['cvmfs']
   }

   exec { "probe ${repository}" :
     command   => "/etc/init.d/cvmfs probe",
     creates   => "/cvmfs/${repository}",
     require   => Service['cvmfs']
   }

}


#########################################################################
#
# Configures a node to use the a local home area for USAtlas VO users
#
#    cvmfs::home::usatlas
# 
#########################################################################

class cvmfs::home::usatlas {

  $remove_nfs_dirs = [ '/share/usatlas' ]

  mount { $remove_nfs_dirs: ensure => absent }

  cvmfs::mkhome::usatlas { 'usatlas1' : }
  cvmfs::mkhome::usatlas { 'usatlas2' : }
  cvmfs::mkhome::usatlas { 'usatlas3' : }
  cvmfs::mkhome::usatlas { 'usatlas4' : }
  
  file { "/share/usatlas" : ensure => directory } 

}


#########################################################################
#
# Configures a node to use the Certficate Authority located in the MWT2 CVMFS repository
#
#    cvmfs::link::certificates
# 
#########################################################################

class cvmfs::link::certificates {

  $remove_nfs_dirs = [ '/share/certificates' ]

  mount { $remove_nfs_dirs: ensure => absent }

  file { '/share/certificates' :
    ensure     => link,
    target     => "/cvmfs/osg.mwt2.org/osg/CA/certificates",
    force      => true,
    require    => [ 
       Package['cvmfs'],
       Mount[$remove_nfs_dirs]
    ]
  }
  file { '/etc/grid-security':
    ensure     => directory,
  }


  file { '/etc/grid-security/certificates' :
    ensure     => link,
    target     => "/share/certificates",
    force      => true,
    require    => [ 
       File['/share/certificates'],
       Mount[$remove_nfs_dirs]
    ]
  }

}


#########################################################################
#
# Configures a node to use the WN-Client located in the MWT2 CVMFS repository
#
#    cvmfs::link::wnclient
#
#########################################################################

class cvmfs::link::wnclient {

  $remove_nfs_dirs = [ '/share/wn-client' ]

  mount { $remove_nfs_dirs: ensure => absent }

    
  file { '/share/wn-client' :
    ensure     => link,
    target     => "/cvmfs/osg.mwt2.org/mwt2/wn-client",
    force      => true,
    require    => [ 
       Package['cvmfs'],
       Mount[$remove_nfs_dirs]
    ]
  }

}


#########################################################################
#
# Configure a node to use the $OSG_APP located in the MWT2 CVMFS repository
#
#    cvmfs::link::app
# 
#########################################################################

class cvmfs::link::app {

  $remove_nfs_dirs = [ '/share/osg' ]

  mount { $remove_nfs_dirs: ensure => absent }


  file { [ '/share/osg', '/share/osg/mwt2' ] :
    ensure     => directory,
    mode       => 755,
    owner      => 'root',
    group      => 'root',
    require    => [ 
       Package['cvmfs'],
       Mount[$remove_nfs_dirs]
    ]
  }

  file { '/osg' :
    ensure     => link,
    target     => "/share/osg",
    require    => Mount[$remove_nfs_dirs],
    force      => true
  }

  file { '/share/osg/mwt2/app' :
    ensure     => link,
    target     => "/cvmfs/osg.mwt2.org/mwt2/app",
    require    => Mount[$remove_nfs_dirs],
    force      => true
  }

}
