#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

#
# https://git.io/JewS5
# export $(grep -E -v '^#' .env | xargs -0)
GITHUB_REPOSITORY="technologiestiftung/dwd-radolan-tree-harvester"
TAG="test"
DOCKERFILE="./Dockerfile"
PUSHIT=
print_usage() {
  printf "\n\nUsage:------------------------------\n"
  printf "Usage: %s -t yourtag\n" "${0}"
  printf "       If -t <tag>   flag is not specified it will use '%s'\n" $TAG
  printf "       If -p         flag is not specified it will not push '%s'\n" $PUSHIT
  # printf "       If -d (Dockerfile) flag is not specified it will use '%s'\n\n\n" $DOCKERFILE
}

while getopts 'pt:s:d:' flag; do
  case "${flag}" in
    t) TAG="${OPTARG}" ;;
    # d) DOCKERFILE="${OPTARG}" ;;
    p) PUSHIT=true ;;
    *) print_usage
       exit 1 ;;
  esac
done




echo "Your image will be build with this repository/tag: '${GITHUB_REPOSITORY}:${TAG}'"
if [[ $PUSHIT == true ]]
then
  echo "and it will be pushed to the docker registry"
else
  echo "it will NOT be pushed to the docker registry"

fi
read -p "Are you sure?(y/n) " -n 1 -r
echo    # (optional) move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
  echo "abort!"
  print_usage
  exit 1
fi

docker build --tag "${GITHUB_REPOSITORY}:${TAG}" -f "${DOCKERFILE}" .
if [[ $PUSHIT == true ]]
then
  echo "push it"
  # docker push "${GITHUB_REPOSITORY}:${TAG}"
fi