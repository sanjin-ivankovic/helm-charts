# Values.yaml Standard Order

This document defines the standard order for sections in `values.yaml` files
across all Helm charts, following Helm/Kubernetes best practices.

## Standard Section Order

1. **Image parameters**
   - `image.repository`
   - `image.tag`
   - `image.imagePullPolicy` / `image.pullPolicy`

2. **Global/Name overrides**
   - `imagePullSecrets`
   - `nameOverride`
   - `fullnameOverride`

3. **Service Account parameters**
   - `serviceAccount.create`
   - `serviceAccount.annotations`
   - `serviceAccount.name`

4. **Deployment parameters**
   - `replicaCount`
   - `updateStrategy`
   - `deploymentStrategy` (fallback)
   - `podAnnotations`
   - `deploymentAnnotations`
   - `statefulSetAnnotations`

5. **Pod spec parameters**
   - `resources`
   - `nodeSelector`
   - `affinity`
   - `tolerations`
   - `securityContext`
   - `podSecurityContext`
   - `topologySpreadConstraints`
   - `priorityClassName`
   - `dnsPolicy`
   - `dnsConfig`
   - `hostNetwork`
   - `hostPort`

6. **Init Container parameters**
   - `initContainer.*`
   - `initContainers`

7. **Service parameters**
   - `service.*`
   - `additionalPorts`
   - `additionalServices`

8. **Ingress parameters**
   - `ingress.*`

9. **Storage parameters**
   - `persistence.*`
   - `additionalVolumes`
   - `additionalMounts`

10. **Application-specific parameters**
    - `env`
    - `envFrom`
    - `probes.*` / `livenessProbe` / `readinessProbe` / `startupProbe`
    - `secrets.*`
    - `database.*`
    - `redis.*`
    - `config.*`
    - `pgadmin.*`
    - `configuration.*`
    - `logLevel`
    - `managed.*`
    - `local.*`
    - `addons.*`
    - `controller.*`

11. **Monitoring parameters**
    - `metrics.*`
    - `serviceMonitor.*`

12. **Autoscaling parameters**
    - `autoscaling.*`

13. **Pod Disruption Budget parameters**
    - `podDisruptionBudget.*`

## Notes

- Sections should be grouped logically and follow Kubernetes resource spec
  ordering where applicable
- Pod spec parameters should be consolidated into a single section
- Application-specific parameters can be further subdivided with subsections as
  needed
- The order prioritizes: image → deployment → pod spec → networking → storage →
  application config → monitoring/autoscaling
