class ixgbe::set_irq_affinity {
  file { "/usr/local/bin/set_irq_affinity.sh": 
    source => "puppet:///modules/ixgbe/set_irq_affinity.sh", 
    require => File['/etc/rc.local.d'] 
  }
} 

class ixgbe::set_irq_affinity::eth4 {
  include ixgbe::set_irq_affinity 
  file { "/etc/rc.local.d/set_irq_affinity.eth4.sh": 
    source => "puppet:///modules/ixgbe/set_irq_affinity.eth4.sh" , 
    require => File['/etc/rc.local.d']
  }
  file { "/etc/rc.local.d/10gtxqueuelen.eth4.sh": 
    source => "puppet:///modules/ixgbe/10gtxqueuelen.eth4.sh", 
    require => File['/etc/rc.local.d']
  }
}

class ixgbe::set_irq_affinity::eth2 {
  include ixgbe::set_irq_affinity
  file { "/etc/rc.local.d/set_irq_affinity.eth2.sh": 
    source => "puppet:///modules/ixgbe/set_irq_affinity.eth2.sh" , 
    require => File['/etc/rc.local.d']
  }
}

class ixgbe::set_irq_affinity::eth0 {
  include ixgbe::set_irq_affinity
  file { "/etc/rc.local.d/set_irq_affinity.eth0.sh": 
    source => "puppet:///modules/ixgbe/set_irq_affinity.eth0.sh" , 
    require => File['/etc/rc.local.d']
  }
  file { "/etc/rc.local.d/10gtxqueuelen.eth0.sh": 
    source => "puppet:///modules/ixgbe/10gtxqueuelen.eth0.sh", 
    require => File['/etc/rc.local.d']
  }
} 
