# Ubuntu 20.04 网络配置

## 配置

vim /etc/netplan/00-installer-config.yaml 
```
# This is the network config written by 'subiquity'
network:
  ethernets:
    enp2s0:
      addresses:
      - 192.168.6.111/24
      gateway4: 192.168.6.1
      nameservers: 
        addresses: [119.29.29.29]
  version: 2
```

## 生效
```
netplan apply
```

## 查看网卡

```
#ethtool  enp2s0 
Settings for enp2s0:
	Supported ports: [ TP MII ]
	Supported link modes:   10baseT/Half 10baseT/Full 
	                        100baseT/Half 100baseT/Full 
	                        1000baseT/Full 
	Supported pause frame use: Symmetric Receive-only
	Supports auto-negotiation: Yes
	Supported FEC modes: Not reported
	Advertised link modes:  10baseT/Half 10baseT/Full 
	                        100baseT/Half 100baseT/Full 
	                        1000baseT/Full 
	Advertised pause frame use: Symmetric Receive-only
	Advertised auto-negotiation: Yes
	Advertised FEC modes: Not reported
	Link partner advertised link modes:  10baseT/Half 10baseT/Full 
	                                     100baseT/Half 100baseT/Full 
	Link partner advertised pause frame use: Symmetric Receive-only
	Link partner advertised auto-negotiation: Yes
	Link partner advertised FEC modes: Not reported
	Speed: 100Mb/s
	Duplex: Full
	Port: MII
	PHYAD: 0
	Transceiver: internal
	Auto-negotiation: on
	Supports Wake-on: pumbg
	Wake-on: d
	Current message level: 0x00000033 (51)
			       drv probe ifdown ifup
	Link detected: yes

```

## 查看网卡驱动

```
#ethtool -i enp2s0 
driver: r8169
version: 
firmware-version: rtl8168g-2_0.0.1 02/06/13
expansion-rom-version: 
bus-info: 0000:02:00.0
supports-statistics: yes
supports-test: no
supports-eeprom-access: no
supports-register-dump: yes
supports-priv-flags: no
```
