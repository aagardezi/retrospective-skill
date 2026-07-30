#!/usr/bin/env bash
# install.sh - Install Retrospective Skill for Antigravity

set -e

SKILL_NAME="retrospective"
TARGET_DIR="${HOME}/.gemini/config/skills/${SKILL_NAME}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Installing Retrospective Skill to ${TARGET_DIR}..."

mkdir -p "${TARGET_DIR}"
cp -r "${SCRIPT_DIR}/SKILL.md" "${TARGET_DIR}/"
cp -r "${SCRIPT_DIR}/scripts" "${TARGET_DIR}/"
cp -r "${SCRIPT_DIR}/references" "${TARGET_DIR}/"
cp -r "${SCRIPT_DIR}/examples" "${TARGET_DIR}/"

echo "Successfully installed ${SKILL_NAME} skill to ${TARGET_DIR}"
echo "You can now run /retro or /retrospective in any Antigravity session!"
