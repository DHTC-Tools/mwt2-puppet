# This defines basic and common requirements for nfs.
# It does not define any particular service or mountpoint set.

# What is needed to be an NFS client? Do not include specific mounts.
class nfs::client {
  file { "/share":
    ensure => directory
  }

  file {
    '/home':
      ensure => '/share/home',
      force => true,
  }

  package {
    'nfs-utils':
      ensure => present;
  }
}

# fix me.
class nfs::client::mwt2::fixme {
  file { '/nfs' : ensure => directory }  
  file { '/nfs/usatlas': ensure => directory } 
}

# Incomplete: what is needed to be an NFS server? Do not
# include specific exports.
class nfs::server {
  package {
    'nfs-utils':
      ensure => present;
  }
}

define nfs::mount($device, $options = 'udp,bg,intr,noatime') { 
  file { "$title" : ensure => directory} 
  mount { "$title": 
    device => $device,
    ensure => mounted,
    fstype => 'nfs',
    require => File["$title"],
    options => $options,
    atboot => true,
  } 
}

