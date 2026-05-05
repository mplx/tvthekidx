#!/bin/bash

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	echo "Error: ${BASH_SOURCE[0]} needs to be sourced"
	exit 1
fi

SCRIPT=$(readlink -f ${BASH_SOURCE[0]})
SCRIPTPATH=$( dirname "$SCRIPT")
PROJECT=$( basename "$SCRIPTPATH")

VENV_PATH="${HOME}/.venv/${PROJECT}"

if [[ -f "${VENV_PATH}/bin/activate" ]]; then
	echo "Activating ${VENV_PATH}/bin/activate"
	source "${VENV_PATH}/bin/activate"
else
	read -rp "venv '${PROJECT}' not found. Create it now? [y/N] " answer
	if [[ "${answer}" =~ ^[Yy]$ ]]; then
		python -m venv "${VENV_PATH}" && source "${VENV_PATH}/bin/activate" && pip install -r "${SCRIPTPATH}/requirements.txt" && echo "venv created and activated"
	else
		echo "Aborted."
	fi
fi
