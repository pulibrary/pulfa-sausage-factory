pulfa-sausage-factory
=====================

Batch process scripts for all Finding Aids digitized content.

The following commands should make sure all your dependencies are installed on a fresh system:

```
curl -L get.rvm.io | bash -s stable
```
```
source "$HOME/.rvm/scripts/rvm"
```
```
rvm install 2.0.0
```
```
rvm use 2.0.0
```
```
rvm --default use 2.0.0
```
```
gem install parseconfig
```
```
gem install nokogiri
```
```
sudo apt-get install python-pyexiv2
```
```
sudo apt-get install pdftk
```

You should be able to run the following from the bin directory:
```
ruby publish.rb {callnumber}
```
