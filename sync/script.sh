#!/bin/bash
set -euo pipefail #make the program exit when failure

echo "[$(date)] The backup starts"
pkill -x lftp || true #kill stale lftp

ergometers_config="${ERGOMETERS_CONFIG}"
ergometers_config="${ergometers_config#\{}" #delete leading {
ergometers_config="${ergometers_config%\}}" #delete trailing }

IFS=',' read -r -a ergometer_entries <<< "${ergometers_config:-}"

for ergometer_entry in "${ergometer_entries[@]}"; do
	ergometer_entry="${ergometer_entry//\"/}" #delete any "
	ergometer_entry="${ergometer_entry//[[:space:]]/}" #delete any spaces
	[[ -z "${ergometer_entry}" ]] && continue #if empty string continue

	ergometer_name="${ergometer_entry%%:*}"
	ergometer_host_with_port="${ergometer_entry#*:}"
	ergometer_host="${ergometer_host_with_port%%:*}"

    # IFS='\n' read -r -a delete_files <<< cat /data/delete

    # for file in "${delete_files[@]}"; do
    #     if [[ -n "${file}" ]]; then
    #         echo "[$(date)] Deleting ${file} on ${ergometer_name}...${ergometer_host}"
    #         rm -f "/data/${file}" || echo "[$(date)] Warning: Failed to delete ${file} locally"
    #         lftp -e "
    #             set net:timeout 10;
    #             set net:max-retries 2;
    #             open ${CYCLUS_USER}:${PASSWORD}@${ergometer_host};
    #             delete ${file};
    #             bye;
    #         " || echo "[$(date)] Warning: Failed to delete ${file} on ${ergometer_name}"
    #     fi
    # done

	for folder in c2d sys prg export; do
                case "${DESTINATION:-/}" in
                        /) remote_folder="${folder}" ;;
                        *) remote_folder="${DESTINATION%/}/${folder}" ;;
                esac

                echo "[$(date)] Syncing ${folder} with ${ergometer_name}...${ergometer_host}"
				echo "with ${CYCLUS_USER} and ${PASSWORD}"

                lftp -e "
                    set net:timeout 10;
                    set net:max-retries 2;
                    open ${CYCLUS_USER}:${PASSWORD}@${ergometer_host};
                    mirror --only-newer ${remote_folder} /data/${folder};
                    mirror -R --only-newer /data/${folder} ${remote_folder};
                    bye;
                " || echo "[$(date)] Warning: Failed to sync ${folder} on ${ergometer_name}"
        done
done

: > /data/delete


