node 'uct2-c200.mwt2.org' {
  include ganglia::client

  class { 'dell::tools':  version => "7.2.0-4.9.1.el6" }

  include ntp::client
  include nfs::client
  include nfs::client::mwt2::fixme
  nfs::mount {'/pnfs'       : device  => '<pnfs-server>:/pnfs',
                              options => 'udp,bg,intr,noac,nosuid,nodev,vers=3' }
  nfs::mount {'/share/home' : device  => '<nfs-server>:/export/home' }
  include mwt2::worker

  condor::install     { "${::hostname}" : version => '7.8.8-110288', start =>  true }
  condor::node::cnode { "${::hostname}" : pool    => 'validation',   core  => 'score' }


  cvmfs::install { "${::hostname}" : version => '2.0.19-1.el6', site => 'uc' }
  include cvmfs::link::certificates
  include cvmfs::link::app
  include cvmfs::link::wnclient
  include cvmfs::home::usatlas

}
