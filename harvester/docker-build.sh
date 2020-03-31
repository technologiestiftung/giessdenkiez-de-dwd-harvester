#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

#
# https://git.io/JewS5
# export $(grep -E -v '^#' .env | xargs -0)
GITHUB_REPOSITORY="technologiestiftung/dwd-radolan-tree-harvester"
TAG="test"
DOCKERFILE="./Dockerfile"
print_usage() {
  printf "\n\nUsage:------------------------------\n"
  printf "Usage: %s -t yourtag\n" "${0}"
  printf "       If -t (tag)        flag is not specified it will use '%s'\n" $TAG
  # printf "       If -d (Dockerfile) flag is not specified it will use '%s'\n\n\n" $DOCKERFILE
}

while getopts 't:s:d:' flag; do
  case "${flag}" in
    t) TAG="${OPTARG}" ;;
    # d) DOCKERFILE="${OPTARG}" ;;
    *) print_usage
       exit 1 ;;
  esac
done




echo "Your image will be build with this repository/tag: '${GITHUB_REPOSITORY}:${TAG}'"

read -p "Are you sure?(y/n) " -n 1 -r
echo    # (optional) move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
  echo "abort!"
  print_usage
  exit 1
fi

docker build --tag "${GITHUB_REPOSITORY}-${SUFFIX}:${TAG}-${STAGE}" -f "${DOCKERFILE}" .

# docker push "${GITHUB_REPOSITORY}-${SUFFIX}:${TAG}-${STAGE}"