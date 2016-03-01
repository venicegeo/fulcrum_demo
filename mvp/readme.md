# Geoshape-Fulcrum MVP

This is a django application which allows the user to connect to a kafka server and ingest data. If the data is a valid geojson feature it can be displayed on a map.

## Requirements

 - Geoshape-Vagrant 
 
## Setup 

Download the geoshape-vagrant repo.
```
https://github.com/ROGUE-JCTD/geoshape-vagrant
```

In an elevated session (sudo or "run as administrator),
change directories to the geoshape-vagrant repo, and install the vagrant hosts updater
```
vagrant plugin install vagrant-hostsupdater
```
Add an entry to the Vagrantfile
```
config.vm.hostname = "geoshape.dev"
```

Bring up the geoshape vm.
```
vagrant up
```

SSH into the VM and run the following commands
```
cd /tmp
wget https://raw.githubusercontent.com/venicegeo/fm-mvp/master/mvp/geoshape_fulcrum_install.sh -O- | tr -d '\r' > /tmp/geoshape_fulcrum_install.sh
sudo bash /tmp/geoshape_fulcrum_install.sh
```
You can modify your fulcrum api key entry in /var/lib/geonode/rogue_geonode/geoshape/local_settings.py
 file (sudo required).
Add any desired filters to the /var/lib/geonode/rogue_geonode/geoshape/local_settings.py file. (US geospatial and phone number filters are added by default.)
Then run the command:
```
sudo geoshape-config init "geoshape.dev"
```

##Known Issues

- Downloading from S3 doesn't work, celery threads need to be properly managed.
- Images are dumped into the fileserver folder, however they may be better presented in mediaroot.
- Sometimes duplicate points are allowed in the same layer.
- Tiles need to be dumped from GeoWebCache based on feature location.  Testing was done to ensure this is NOT a browser issue but rather a server issue.
- Unit tests need to be done.
- An installer should be created and versioned.

## Bugs

Todo