#!/bin/bash

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	echo "Error: ${BASH_SOURCE[0]} needs to be sourced"
	exit 1
fi

SCRIPT=$(readlink -f ${BASH_SOURCE[0]})
SCRIPTPATH=$( dirname "$SCRIPT")
PROJECT=$( basename "$SCRIPTPATH")

echo "Activating ${HOME}/.venv/${PROJECT}/bin/activate"
if [[ -f "${HOME}/.venv/${PROJECT}/bin/activate" ]]; then
	source "${HOME}/.venv/${PROJECT}/bin/activate"
else
	echo "Error: cannot find venv '${PROJECT}'"
fi
