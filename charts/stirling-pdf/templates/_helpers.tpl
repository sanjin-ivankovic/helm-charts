{{/*
Expand the name of the chart.
*/}}
{{- define "stirling-pdf.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "stirling-pdf.fullname" -}}
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
{{- define "stirling-pdf.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "stirling-pdf.labels" -}}
helm.sh/chart: {{ include "stirling-pdf.chart" . }}
{{ include "stirling-pdf.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
Uses Kubernetes recommended labels for better tooling compatibility
Note: If existing deployment uses 'app: {{ .Release.Name }}', it may need to be recreated
*/}}
{{- define "stirling-pdf.selectorLabels" -}}
app.kubernetes.io/name: {{ include "stirling-pdf.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the PVC
*/}}
{{- define "stirling-pdf.pvcName" -}}
{{- printf "%s-data" (include "stirling-pdf.fullname" .) }}
{{- end }}
