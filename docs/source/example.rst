Wiki Pages

{{>toc}}

*[[Big Picture Overview]]*

* Portlets and Software
** [[QWizard Documentation]]
** [[content of portlet.properties]]
** [[ETL script/dropbox information]]
** [[Virtualization_Infrastructure_HOWTO|How To use our virtualization infrastructure (including Firefly)]]
** [[How to Test our Software]]
** [[Neat Java/Liferay/Tomcat Tricks/Solutions to Common Problems]]
** [[Password reset daemon]]
* Workflows
** [[gUSE submitter ideas]]
** [[QBiC specific modules and how to update them]]
* Settings and other Info
** [[Changes_to_qbisopenBIS_SSL_settings|Changes to qbis and openBIS settings]]
** [[openBIS LDAP connection]]
** [[HiWi Section]]
* Servers
** [[Printer Server]]
** [[KNIME Server]]
** [[Production Portal]]
** [[add_user_on_data|Procedure to add a new data mover user to data]]
* Storage
** [[ICGC Storage]]
* Misc
** [[QBiC LDAP]]
** [[msconvert]]
** [[QWin with RDP]]
** [[qflow-master]]
** URL to apply for a cluster account: http://www.zdv.uni-tuebingen.de/dienstleistungen/computing/zugang-zu-den-ressourcen.html
** Documentation wiki for the Core Facility Hardware on the ZDV redmine: https://hpcmgmt.zdv.uni-tuebingen.de/projects/core-facility-hardware/wiki

SSH ProxyCommand
================

This is a useful way to access a server which is not possible to access directly, due to network routing or firewall issues. You need an account on the machine acting as a proxy, in the example below playground1.

::


  Host *.local
          ProxyCommand ssh -q -l <your username here> playground1.qbic.uni-tuebingen.de nc %h 22
          IdentityFile ~/.ssh/id_rsa_qbic

With this configuration SSH will for call the proxy command and then pipe the ssh command from the command line trough. For example:

::


  ssh -l yourusernamehere portal-new.local
  scp something yourusernamehere@portal-new.local:/some/where
  rsync something yourusernamehere@portal-new.local:/some/where
  ssh -l yourusernamehere portal-new.local -L 127.0.0.1:8080:127.0.0.1:8080 -L 127.0.0.3:8080:127.0.0.3:8080

Will now work as expected, with the only difference the password (or ssh key pass phrase) will be asked twice, the first time to ssh to the ProxyHost (playground) the second time to access the target host.

Note the ProxyCommand doesn't have to be an ssh command, it can be any command, so be crazy!

Additional step for OS X users
------------------------------

If you need to forward a local IP like 127.0.0.3 (and not .1) you'll get an error like "cannot assign requested address". One possible solution is to add the IP to the lo0 interface with a command like

    ifconfig lo0 add 127.0.0.3/32

A couple of words about the pre production setup
================================================

The new portal VM will provide a standalone Liferay for our main website and all the portlets not needing gUSE interaction or able to work using the gUSE remote API only. The qbicnavigator and the wizard portlets are an example. The VM will also provide a gUSE instance served by a separate tomcat server and user (note this instance has its own Liferay bundled with gUSE). The two functional (and local to this machine) users are named respectively tomcat-liferay and tomcat-guse, the home directories being /home/$USER. QBiC staff members able to ssh into this machine should be able to change to the mentioned users by using sudo -i -u $USER. If not please contact Enrico.

Standalone Liferay
------------------

At the time of writing this is Liferay 6.2 GA3 released on Jan. 15th 2015. The Liferay home directory (as per Liferay terminology this is suggested to be the install base directory) is @/home/tomcat-liferay/liferay_production/@ and the tomcat base directory (defined by the environment variable CATALINA_BASE) is @/home/tomcat-liferay/liferay_production/tomcat/@ where all Liferay specific libraries, portlets, logs and configuration files can be found. The tomcat binaries and init script (well systemd services) are from the Red Hat provided tomcat package, based on tomcat 7.0.42. *Do not use startup.sh* or similar to start tomcat. Tomcat can be started, stopped and the status can be checked by using systemctl <command> tomcat-liferay.service. The systemd unit file can be found at @/etc/systemd/system/tomcat-liferay.service@ and the tomcat configuration file (where all the tomcat environment variables are read from) can be found at @/etc/sysconfig/tomcat-liferay@. Liferay is accessible from tomcat at the /portal/ URL.

gUSE
----

Version of gUSE is 3.7.0. gUSE was installed in folder @/home/tomcat-guse/guse_original_install/@ and then the folder has been moved to @/home/tomcat-guse/guse_original_install.donottouchme/@ to preserve a copy of the fresh installation should it be needed. *Please don't touch this folder*. The original install has been copied to /home/tomcat-guse/guse_production/ and then modified (removed bundled tomcat and libraries). Erhan modified information (wizzard) portlet was also included here, but before that an additional copy of the folder was done in /home/tomcat-guse/guse_production.broken/. So gUSE and Liferay installation home directory is /home/tomcat-guse/guse_production/ (Liferay and gUSE config files have been modified to reflect this). The tomcat base directory (defined by the environment variable CATALINA_BASE) is @/home/tomcat-guse/guse_production/apache-tomcat-7.0.55/@. As for the standalone Liferay the tomcat binaries and init script (well systemd services) are from the Red Hat provided tomcat package, based on tomcat 7.0.42. *Do not use startup.sh* or similar to start tomcat. Tomcat can be started, stopped and the status can be checked by using systemctl <command> tomcat-guse.service. The systemd unit file can be found at @/etc/systemd/system/tomcat-guse.service@ and the tomcat configuration file (where all the tomcat environment variables are read from) can be found at @/etc/sysconfig/tomcat-guse@.

Remote API
~~~~~~~~~~

Remote API is enabled and accessible from localhost only (for now). Since both Liferay and gUSE are on the same machine nothing more than this should be required. There is no password since the request comes from localhost. Remote API debug is also enabled to easy the task of developing using it. Debug information can be found in the catalina.out log file in the tomcat BASE directory for gUSE @/home/tomcat-guse/guse_production/apache-tomcat-7.0.55/@.

If necessary Remote API access can be enabled from everywhere via the Apache HTTPD reverse proxy, but a password will be requested for a foreign request.

gUSE service initialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~

One of the biggest problems of gUSE is its inability to automatically start. This is a major deficiency and we have no solution for the problem yet. Liferay autostarts correctly unattended, gUSE requires the user to execute the "Wizzard". Due to massive limitations in this components the only way of executing it is when using the [[Wiki#SSH-tunnel-with-proxy-command|SSH tunnel with proxy command]], it cannot work when using the SSH SOCKS proxy.

*Please don't try the gUSE service initialization (the wizzard) yourself!*. Ask Enrico first. If you break it I'll search for you! Access the Wizzard page http://127.0.0.1:8080/information/, User is admin, the password is in the clear text config file tomcat-users.xml in the tomcat conf directory.

For reference following are the parameters
* JDBC Driver: org.gjt.mm.mysql.Driver (that'S the default)
* URI: jdbc:mysql://127.0.0.1:3306/guse
* User: guse
* Password: guse (..... I know.....)

At the next screen uncheck the permission, look at the awesome animation and pray everything works.

Apache HTTPD reverse proxy
--------------------------

gUSE makes the matter of setting up a reverse proxy unnecessary complicated. While the standalone Liferay installation has been moved into the /portal/ subfolder from the ROOT one very easily, gUSE provided Liferay might be a different story. It might be possible to move it and restore everything breaking, but at the next gUSE update disaster is expected. So an alternative solution, less elegant but without the upgrade super-nightmare scenario is to access the gUSE services from a different port, matching a different virtual server in the Apache configuration file. Apache is currently configured the following way:
* Request incoming on port 80 -> redirect to HTTPS (port 443) unconditionally
* Request incoming on port 443 with HTTP request Host header matching "portal.qbic.uni-tuebingen.de" -> proxy to standalone Liferay (with few uninportant exceptions)
* Request incoming on port 8443 with HTTP request Host header matching "portal.qbic.uni-tuebingen.de" -> proxy to gUSE (with quite a few exceptions)

The most notable exception is the gUSE Wizard, which seems to be broken when 1) not using a public IP, 2) when used behind a reverse proxy. Wizzard must run from SSH tunnel proxy. The remote API is also not proxyed since it is supposed to be accessed locally only (from the standalone Liferay) and such request can be dispatched directly.

