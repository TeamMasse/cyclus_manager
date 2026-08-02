#!/bin/bash
set -euo pipefail

echo "[$(date)] The backup starts"
pkill -x lftp || true

ergometers_config="${ERGOMETERS_CONFIG:-${ergometers_config:-}}"
ergometers_config="${ergometers_config#\{}"
ergometers_config="${ergometers_config%\}}"

IFS=',' read -r -a ergometer_entries <<< "${ergometers_config:-}"

for ergometer_entry in "${ergometer_entries[@]}"; do
	ergometer_entry="${ergometer_entry//\"/}"
	ergometer_entry="${ergometer_entry//[[:space:]]/}"
	[[ -z "${ergometer_entry}" ]] && continue

	ergometer_name="${ergometer_entry%%:*}"
	ergometer_host_with_port="${ergometer_entry#*:}"
	ergometer_host="${ergometer_host_with_port%%:*}"

	echo "[$(date)] Syncing c2d and sys to ${ergometer_name} (${ergometer_host})"

	for folder in c2d sys prg export; do
		case "${DESTINATION:-/}" in
			/) remote_folder="/${folder}" ;;
			*) remote_folder="${DESTINATION%/}/${folder}" ;;
		esac

		lftp -u "${USER},${PASSWORD}" "ftp://${ergometer_host}:21" -e "mirror -R --only-newer /data/${folder} ${remote_folder}; bye"
	done
done