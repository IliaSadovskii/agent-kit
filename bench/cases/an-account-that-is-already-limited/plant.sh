#!/bin/sh
set -e
$KIT limit set fake --until 2027-01-01T00:00:00+00:00 --said-by "another/build"
