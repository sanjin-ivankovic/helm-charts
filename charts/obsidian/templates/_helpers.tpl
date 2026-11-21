{{/*
Expand the name of the chart.
*/}}
{{- define "obsidian.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "obsidian.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "obsidian.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels (no component; each workload adds its own).
*/}}
{{- define "obsidian.labels" -}}
helm.sh/chart: {{ include "obsidian.chart" . }}
app.kubernetes.io/name: {{ include "obsidian.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels for the desktop. The component label keeps the two Services
apart; selectors are immutable, so never change it on a released chart.
*/}}
{{- define "obsidian.selectorLabels" -}}
app.kubernetes.io/name: {{ include "obsidian.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: app
{{- end }}

{{/*
Name of the /config PVC
*/}}
{{- define "obsidian.pvcName" -}}
{{- printf "%s-config" (include "obsidian.fullname" .) }}
{{- end }}

{{/*
CouchDB names and selector labels
*/}}
{{- define "obsidian.couchdb.fullname" -}}
{{- printf "%s-couchdb" (include "obsidian.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "obsidian.couchdb.selectorLabels" -}}
app.kubernetes.io/name: {{ include "obsidian.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: couchdb
{{- end }}

{{- define "obsidian.couchdb.pvcName" -}}
{{- printf "%s-data" (include "obsidian.couchdb.fullname" .) }}
{{- end }}
