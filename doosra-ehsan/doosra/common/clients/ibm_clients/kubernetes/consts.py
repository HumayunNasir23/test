FAILED = "failed"

CLASSIC_BLOCK_STORAGE_CLASSES = ['ibmc-block-bronze', 'ibmc-block-retain-bronze', 'ibmc-block-retain-silver',
                                 'ibmc-block-silver', 'ibmc-block-gold', 'ibmc-block-retain-gold']

VELERO_INSTALLATION_FAILED = "BACKUP, Failed kindly check internet connectivity of cluster and check the CPU " \
                             "and Memory Limit and Requests "
BUCKET_CREATION_ERROR = "BUCKET CREATION, Unable to Create Bucket"

# Velero and Restic Manifests

BACKUP_CRD = r'''
{
      "apiVersion": "apiextensions.k8s.io/v1beta1",
      "kind": "CustomResourceDefinition",
      "metadata": {
        "annotations": {
          "controller-gen.kubebuilder.io/version": "v0.3.0"
        },
        "labels": {
          "component": "velero"
        },
        "name": "backups.velero.io"
      },
      "spec": {
        "group": "velero.io",
        "names": {
          "kind": "Backup",
          "listKind": "BackupList",
          "plural": "backups",
          "singular": "backup"
        },
        "preserveUnknownFields": false,
        "scope": "Namespaced",
        "validation": {
          "openAPIV3Schema": {
            "description": "",
            "properties": {
              "apiVersion": {
                "description": "",
                "type": "string"
              },
              "kind": {
                "description": "",
                "type": "string"
              },
              "metadata": {
                "type": "object"
              },
              "spec": {
                "description": "",
                "properties": {
                  "defaultVolumesToRestic": {
                    "description": "",
                    "type": "boolean"
                  },
                  "excludedNamespaces": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "excludedResources": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "hooks": {
                    "description": "",
                    "properties": {
                      "resources": {
                        "description": "",
                        "items": {
                          "description": "",
                          "properties": {
                            "excludedNamespaces": {
                              "description": "",
                              "items": {
                                "type": "string"
                              },
                              "nullable": true,
                              "type": "array"
                            },
                            "excludedResources": {
                              "description": "",
                              "items": {
                                "type": "string"
                              },
                              "nullable": true,
                              "type": "array"
                            },
                            "includedNamespaces": {
                              "description": "",
                              "items": {
                                "type": "string"
                              },
                              "nullable": true,
                              "type": "array"
                            },
                            "includedResources": {
                              "description": "",
                              "items": {
                                "type": "string"
                              },
                              "nullable": true,
                              "type": "array"
                            },
                            "labelSelector": {
                              "description": "",
                              "nullable": true,
                              "properties": {
                                "matchExpressions": {
                                  "description": "",
                                  "items": {
                                    "description": "",
                                    "properties": {
                                      "key": {
                                        "description": "",
                                        "type": "string"
                                      },
                                      "operator": {
                                        "description": "",
                                        "type": "string"
                                      },
                                      "values": {
                                        "description": "",
                                        "items": {
                                          "type": "string"
                                        },
                                        "type": "array"
                                      }
                                    },
                                    "required": [
                                      "key",
                                      "operator"
                                    ],
                                    "type": "object"
                                  },
                                  "type": "array"
                                },
                                "matchLabels": {
                                  "additionalProperties": {
                                    "type": "string"
                                  },
                                  "description": "",
                                  "type": "object"
                                }
                              },
                              "type": "object"
                            },
                            "name": {
                              "description": "",
                              "type": "string"
                            },
                            "post": {
                              "description": "",
                              "items": {
                                "description": "",
                                "properties": {
                                  "exec": {
                                    "description": "",
                                    "properties": {
                                      "command": {
                                        "description": "",
                                        "items": {
                                          "type": "string"
                                        },
                                        "minItems": 1,
                                        "type": "array"
                                      },
                                      "container": {
                                        "description": "",
                                        "type": "string"
                                      },
                                      "onError": {
                                        "description": "",
                                        "enum": [
                                          "Continue",
                                          "Fail"
                                        ],
                                        "type": "string"
                                      },
                                      "timeout": {
                                        "description": "",
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "command"
                                    ],
                                    "type": "object"
                                  }
                                },
                                "required": [
                                  "exec"
                                ],
                                "type": "object"
                              },
                              "type": "array"
                            },
                            "pre": {
                              "description": "",
                              "items": {
                                "description": "",
                                "properties": {
                                  "exec": {
                                    "description": "",
                                    "properties": {
                                      "command": {
                                        "description": "",
                                        "items": {
                                          "type": "string"
                                        },
                                        "minItems": 1,
                                        "type": "array"
                                      },
                                      "container": {
                                        "description": "",
                                        "type": "string"
                                      },
                                      "onError": {
                                        "description": "",
                                        "enum": [
                                          "Continue",
                                          "Fail"
                                        ],
                                        "type": "string"
                                      },
                                      "timeout": {
                                        "description": "",
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "command"
                                    ],
                                    "type": "object"
                                  }
                                },
                                "required": [
                                  "exec"
                                ],
                                "type": "object"
                              },
                              "type": "array"
                            }
                          },
                          "required": [
                            "name"
                          ],
                          "type": "object"
                        },
                        "nullable": true,
                        "type": "array"
                      }
                    },
                    "type": "object"
                  },
                  "includeClusterResources": {
                    "description": "",
                    "nullable": true,
                    "type": "boolean"
                  },
                  "includedNamespaces": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "includedResources": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "labelSelector": {
                    "description": "",
                    "nullable": true,
                    "properties": {
                      "matchExpressions": {
                        "description": "",
                        "items": {
                          "description": "",
                          "properties": {
                            "key": {
                              "description": "",
                              "type": "string"
                            },
                            "operator": {
                              "description": "",
                              "type": "string"
                            },
                            "values": {
                              "description": "",
                              "items": {
                                "type": "string"
                              },
                              "type": "array"
                            }
                          },
                          "required": [
                            "key",
                            "operator"
                          ],
                          "type": "object"
                        },
                        "type": "array"
                      },
                      "matchLabels": {
                        "additionalProperties": {
                          "type": "string"
                        },
                        "description": "",
                        "type": "object"
                      }
                    },
                    "type": "object"
                  },
                  "orderedResources": {
                    "additionalProperties": {
                      "type": "string"
                    },
                    "description": "",
                    "nullable": true,
                    "type": "object"
                  },
                  "snapshotVolumes": {
                    "description": "",
                    "nullable": true,
                    "type": "boolean"
                  },
                  "storageLocation": {
                    "description": "",
                    "type": "string"
                  },
                  "ttl": {
                    "description": "",
                    "type": "string"
                  },
                  "volumeSnapshotLocations": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  }
                },
                "type": "object"
              },
              "status": {
                "description": "",
                "properties": {
                  "completionTimestamp": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "errors": {
                    "description": "",
                    "type": "integer"
                  },
                  "expiration": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "formatVersion": {
                    "description": "",
                    "type": "string"
                  },
                  "phase": {
                    "description": "",
                    "enum": [
                      "New",
                      "FailedValidation",
                      "InProgress",
                      "Completed",
                      "PartiallyFailed",
                      "Failed",
                      "Deleting"
                    ],
                    "type": "string"
                  },
                  "progress": {
                    "description": "",
                    "nullable": true,
                    "properties": {
                      "itemsBackedUp": {
                        "description": "",
                        "type": "integer"
                      },
                      "totalItems": {
                        "description": "",
                        "type": "integer"
                      }
                    },
                    "type": "object"
                  },
                  "startTimestamp": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "validationErrors": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "version": {
                    "description": "",
                    "type": "integer"
                  },
                  "volumeSnapshotsAttempted": {
                    "description": "",
                    "type": "integer"
                  },
                  "volumeSnapshotsCompleted": {
                    "description": "",
                    "type": "integer"
                  },
                  "warnings": {
                    "description": "",
                    "type": "integer"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          }
        },
        "version": "v1",
        "versions": [
          {
            "name": "v1",
            "served": true,
            "storage": true
          }
        ]
      }
    }
'''

BACKUP_STORAGE_CRD = r'''
{
      "apiVersion": "apiextensions.k8s.io/v1beta1",
      "kind": "CustomResourceDefinition",
      "metadata": {
        "annotations": {
          "controller-gen.kubebuilder.io/version": "v0.3.0"
        },
        "labels": {
          "component": "velero"
        },
        "name": "backupstoragelocations.velero.io"
      },
      "spec": {
        "additionalPrinterColumns": [
          {
            "JSONPath": ".status.phase",
            "description": "",
            "name": "Phase",
            "type": "string"
          },
          {
            "JSONPath": ".status.lastValidationTime",
            "description": "",
            "name": "Last Validated",
            "type": "date"
          },
          {
            "JSONPath": ".metadata.creationTimestamp",
            "name": "Age",
            "type": "date"
          }
        ],
        "group": "velero.io",
        "names": {
          "kind": "BackupStorageLocation",
          "listKind": "BackupStorageLocationList",
          "plural": "backupstoragelocations",
          "shortNames": [
            "bsl"
          ],
          "singular": "backupstoragelocation"
        },
        "preserveUnknownFields": false,
        "scope": "Namespaced",
        "subresources": {
          "status": {}
        },
        "validation": {
          "openAPIV3Schema": {
            "description": "",
            "properties": {
              "apiVersion": {
                "description": "",
                "type": "string"
              },
              "kind": {
                "description": "",
                "type": "string"
              },
              "metadata": {
                "type": "object"
              },
              "spec": {
                "description": "",
                "properties": {
                  "accessMode": {
                    "description": "",
                    "enum": [
                      "ReadOnly",
                      "ReadWrite"
                    ],
                    "type": "string"
                  },
                  "backupSyncPeriod": {
                    "description": "",
                    "nullable": true,
                    "type": "string"
                  },
                  "config": {
                    "additionalProperties": {
                      "type": "string"
                    },
                    "description": "",
                    "type": "object"
                  },
                  "objectStorage": {
                    "description": "",
                    "properties": {
                      "bucket": {
                        "description": "",
                        "type": "string"
                      },
                      "caCert": {
                        "description": "",
                        "format": "byte",
                        "type": "string"
                      },
                      "prefix": {
                        "description": "",
                        "type": "string"
                      }
                    },
                    "required": [
                      "bucket"
                    ],
                    "type": "object"
                  },
                  "provider": {
                    "description": "",
                    "type": "string"
                  },
                  "validationFrequency": {
                    "description": "",
                    "nullable": true,
                    "type": "string"
                  }
                },
                "required": [
                  "objectStorage",
                  "provider"
                ],
                "type": "object"
              },
              "status": {
                "description": "",
                "properties": {
                  "accessMode": {
                    "description": "",
                    "enum": [
                      "ReadOnly",
                      "ReadWrite"
                    ],
                    "type": "string"
                  },
                  "lastSyncedRevision": {
                    "description": "",
                    "type": "string"
                  },
                  "lastSyncedTime": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "lastValidationTime": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "phase": {
                    "description": "",
                    "enum": [
                      "Available",
                      "Unavailable"
                    ],
                    "type": "string"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          }
        },
        "version": "v1",
        "versions": [
          {
            "name": "v1",
            "served": true,
            "storage": true
          }
        ]
      }
    }
'''

DELETE_BACKUP_REQ_CRD = r'''
{
      "apiVersion": "apiextensions.k8s.io/v1beta1",
      "kind": "CustomResourceDefinition",
      "metadata": {
        "annotations": {
          "controller-gen.kubebuilder.io/version": "v0.3.0"
        },
        "labels": {
          "component": "velero"
        },
        "name": "deletebackuprequests.velero.io"
      },
      "spec": {
        "group": "velero.io",
        "names": {
          "kind": "DeleteBackupRequest",
          "listKind": "DeleteBackupRequestList",
          "plural": "deletebackuprequests",
          "singular": "deletebackuprequest"
        },
        "preserveUnknownFields": false,
        "scope": "Namespaced",
        "validation": {
          "openAPIV3Schema": {
            "description": "",
            "properties": {
              "apiVersion": {
                "description": "",
                "type": "string"
              },
              "kind": {
                "description": "",
                "type": "string"
              },
              "metadata": {
                "type": "object"
              },
              "spec": {
                "description": "",
                "properties": {
                  "backupName": {
                    "type": "string"
                  }
                },
                "required": [
                  "backupName"
                ],
                "type": "object"
              },
              "status": {
                "description": "",
                "properties": {
                  "errors": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "phase": {
                    "description": "",
                    "enum": [
                      "New",
                      "InProgress",
                      "Processed"
                    ],
                    "type": "string"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          }
        },
        "version": "v1",
        "versions": [
          {
            "name": "v1",
            "served": true,
            "storage": true
          }
        ]
      }
    }
'''

DOWNLOAD_REQ_CRD = r'''
{
      "apiVersion": "apiextensions.k8s.io/v1beta1",
      "kind": "CustomResourceDefinition",
      "metadata": {
        "annotations": {
          "controller-gen.kubebuilder.io/version": "v0.3.0"
        },
        "labels": {
          "component": "velero"
        },
        "name": "downloadrequests.velero.io"
      },
      "spec": {
        "group": "velero.io",
        "names": {
          "kind": "DownloadRequest",
          "listKind": "DownloadRequestList",
          "plural": "downloadrequests",
          "singular": "downloadrequest"
        },
        "preserveUnknownFields": false,
        "scope": "Namespaced",
        "validation": {
          "openAPIV3Schema": {
            "description": "",
            "properties": {
              "apiVersion": {
                "description": "",
                "type": "string"
              },
              "kind": {
                "description": "",
                "type": "string"
              },
              "metadata": {
                "type": "object"
              },
              "spec": {
                "description": "",
                "properties": {
                  "target": {
                    "description": "",
                    "properties": {
                      "kind": {
                        "description": "",
                        "enum": [
                          "BackupLog",
                          "BackupContents",
                          "BackupVolumeSnapshots",
                          "BackupResourceList",
                          "RestoreLog",
                          "RestoreResults"
                        ],
                        "type": "string"
                      },
                      "name": {
                        "description": "",
                        "type": "string"
                      }
                    },
                    "required": [
                      "kind",
                      "name"
                    ],
                    "type": "object"
                  }
                },
                "required": [
                  "target"
                ],
                "type": "object"
              },
              "status": {
                "description": "",
                "properties": {
                  "downloadURL": {
                    "description": "",
                    "type": "string"
                  },
                  "expiration": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "phase": {
                    "description": "",
                    "enum": [
                      "New",
                      "Processed"
                    ],
                    "type": "string"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          }
        },
        "version": "v1",
        "versions": [
          {
            "name": "v1",
            "served": true,
            "storage": true
          }
        ]
      }
    }
'''

POD_VOLUME_BACKUP_CRD = r'''
{
      "apiVersion": "apiextensions.k8s.io/v1beta1",
      "kind": "CustomResourceDefinition",
      "metadata": {
        "annotations": {
          "controller-gen.kubebuilder.io/version": "v0.3.0"
        },
        "labels": {
          "component": "velero"
        },
        "name": "podvolumebackups.velero.io"
      },
      "spec": {
        "group": "velero.io",
        "names": {
          "kind": "PodVolumeBackup",
          "listKind": "PodVolumeBackupList",
          "plural": "podvolumebackups",
          "singular": "podvolumebackup"
        },
        "preserveUnknownFields": false,
        "scope": "Namespaced",
        "validation": {
          "openAPIV3Schema": {
            "properties": {
              "apiVersion": {
                "description": "",
                "type": "string"
              },
              "kind": {
                "description": "",
                "type": "string"
              },
              "metadata": {
                "type": "object"
              },
              "spec": {
                "description": "",
                "properties": {
                  "backupStorageLocation": {
                    "description": "",
                    "type": "string"
                  },
                  "node": {
                    "description": "",
                    "type": "string"
                  },
                  "pod": {
                    "description": "",
                    "properties": {
                      "apiVersion": {
                        "description": "",
                        "type": "string"
                      },
                      "fieldPath": {
                        "description": "",
                        "type": "string"
                      },
                      "kind": {
                        "description": "",
                        "type": "string"
                      },
                      "name": {
                        "description": "",
                        "type": "string"
                      },
                      "namespace": {
                        "description": "",
                        "type": "string"
                      },
                      "resourceVersion": {
                        "description": "",
                        "type": "string"
                      },
                      "uid": {
                        "description": "",
                        "type": "string"
                      }
                    },
                    "type": "object"
                  },
                  "repoIdentifier": {
                    "description": "",
                    "type": "string"
                  },
                  "tags": {
                    "additionalProperties": {
                      "type": "string"
                    },
                    "description": "",
                    "type": "object"
                  },
                  "volume": {
                    "description": "",
                    "type": "string"
                  }
                },
                "required": [
                  "backupStorageLocation",
                  "node",
                  "pod",
                  "repoIdentifier",
                  "volume"
                ],
                "type": "object"
              },
              "status": {
                "description": "",
                "properties": {
                  "completionTimestamp": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "message": {
                    "description": "",
                    "type": "string"
                  },
                  "path": {
                    "description": "",
                    "type": "string"
                  },
                  "phase": {
                    "description": "",
                    "enum": [
                      "New",
                      "InProgress",
                      "Completed",
                      "Failed"
                    ],
                    "type": "string"
                  },
                  "progress": {
                    "description": "",
                    "properties": {
                      "bytesDone": {
                        "format": "int64",
                        "type": "integer"
                      },
                      "totalBytes": {
                        "format": "int64",
                        "type": "integer"
                      }
                    },
                    "type": "object"
                  },
                  "snapshotID": {
                    "description": "",
                    "type": "string"
                  },
                  "startTimestamp": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          }
        },
        "version": "v1",
        "versions": [
          {
            "name": "v1",
            "served": true,
            "storage": true
          }
        ]
      }
    }
'''

POD_VOLUME_RESTORE_CRD = r'''
{
      "apiVersion": "apiextensions.k8s.io/v1beta1",
      "kind": "CustomResourceDefinition",
      "metadata": {
        "annotations": {
          "controller-gen.kubebuilder.io/version": "v0.3.0"
        },
        "labels": {
          "component": "velero"
        },
        "name": "podvolumerestores.velero.io"
      },
      "spec": {
        "group": "velero.io",
        "names": {
          "kind": "PodVolumeRestore",
          "listKind": "PodVolumeRestoreList",
          "plural": "podvolumerestores",
          "singular": "podvolumerestore"
        },
        "preserveUnknownFields": false,
        "scope": "Namespaced",
        "validation": {
          "openAPIV3Schema": {
            "properties": {
              "apiVersion": {
                "description": "",
                "type": "string"
              },
              "kind": {
                "description": "",
                "type": "string"
              },
              "metadata": {
                "type": "object"
              },
              "spec": {
                "description": "",
                "properties": {
                  "backupStorageLocation": {
                    "description": "",
                    "type": "string"
                  },
                  "pod": {
                    "description": "",
                    "properties": {
                      "apiVersion": {
                        "description": "",
                        "type": "string"
                      },
                      "fieldPath": {
                        "description": "",
                        "type": "string"
                      },
                      "kind": {
                        "description": "",
                        "type": "string"
                      },
                      "name": {
                        "description": "",
                        "type": "string"
                      },
                      "namespace": {
                        "description": "",
                        "type": "string"
                      },
                      "resourceVersion": {
                        "description": "",
                        "type": "string"
                      },
                      "uid": {
                        "description": "",
                        "type": "string"
                      }
                    },
                    "type": "object"
                  },
                  "repoIdentifier": {
                    "description": "",
                    "type": "string"
                  },
                  "snapshotID": {
                    "description": "",
                    "type": "string"
                  },
                  "volume": {
                    "description": "",
                    "type": "string"
                  }
                },
                "required": [
                  "backupStorageLocation",
                  "pod",
                  "repoIdentifier",
                  "snapshotID",
                  "volume"
                ],
                "type": "object"
              },
              "status": {
                "description": "",
                "properties": {
                  "completionTimestamp": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "message": {
                    "description": "",
                    "type": "string"
                  },
                  "phase": {
                    "description": "",
                    "enum": [
                      "New",
                      "InProgress",
                      "Completed",
                      "Failed"
                    ],
                    "type": "string"
                  },
                  "progress": {
                    "description": "",
                    "properties": {
                      "bytesDone": {
                        "format": "int64",
                        "type": "integer"
                      },
                      "totalBytes": {
                        "format": "int64",
                        "type": "integer"
                      }
                    },
                    "type": "object"
                  },
                  "startTimestamp": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          }
        },
        "version": "v1",
        "versions": [
          {
            "name": "v1",
            "served": true,
            "storage": true
          }
        ]
      }
    }
'''

RESTIC_REPO_CRD = r'''
{
      "apiVersion": "apiextensions.k8s.io/v1beta1",
      "kind": "CustomResourceDefinition",
      "metadata": {
        "annotations": {
          "controller-gen.kubebuilder.io/version": "v0.3.0"
        },
        "labels": {
          "component": "velero"
        },
        "name": "resticrepositories.velero.io"
      },
      "spec": {
        "group": "velero.io",
        "names": {
          "kind": "ResticRepository",
          "listKind": "ResticRepositoryList",
          "plural": "resticrepositories",
          "singular": "resticrepository"
        },
        "preserveUnknownFields": false,
        "scope": "Namespaced",
        "validation": {
          "openAPIV3Schema": {
            "properties": {
              "apiVersion": {
                "description": "",
                "type": "string"
              },
              "kind": {
                "description": "",
                "type": "string"
              },
              "metadata": {
                "type": "object"
              },
              "spec": {
                "description": "",
                "properties": {
                  "backupStorageLocation": {
                    "description": "",
                    "type": "string"
                  },
                  "maintenanceFrequency": {
                    "description": "",
                    "type": "string"
                  },
                  "resticIdentifier": {
                    "description": "",
                    "type": "string"
                  },
                  "volumeNamespace": {
                    "description": "",
                    "type": "string"
                  }
                },
                "required": [
                  "backupStorageLocation",
                  "maintenanceFrequency",
                  "resticIdentifier",
                  "volumeNamespace"
                ],
                "type": "object"
              },
              "status": {
                "description": "",
                "properties": {
                  "lastMaintenanceTime": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "message": {
                    "description": "",
                    "type": "string"
                  },
                  "phase": {
                    "description": "",
                    "enum": [
                      "New",
                      "Ready",
                      "NotReady"
                    ],
                    "type": "string"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          }
        },
        "version": "v1",
        "versions": [
          {
            "name": "v1",
            "served": true,
            "storage": true
          }
        ]
      }
    }
'''

RESTORE_CRD = r'''
{
      "apiVersion": "apiextensions.k8s.io/v1beta1",
      "kind": "CustomResourceDefinition",
      "metadata": {
        "annotations": {
          "controller-gen.kubebuilder.io/version": "v0.3.0"
        },
        "labels": {
          "component": "velero"
        },
        "name": "restores.velero.io"
      },
      "spec": {
        "group": "velero.io",
        "names": {
          "kind": "Restore",
          "listKind": "RestoreList",
          "plural": "restores",
          "singular": "restore"
        },
        "preserveUnknownFields": false,
        "scope": "Namespaced",
        "validation": {
          "openAPIV3Schema": {
            "description": "",
            "properties": {
              "apiVersion": {
                "description": "",
                "type": "string"
              },
              "kind": {
                "description": "",
                "type": "string"
              },
              "metadata": {
                "type": "object"
              },
              "spec": {
                "description": "",
                "properties": {
                  "backupName": {
                    "description": "",
                    "type": "string"
                  },
                  "excludedNamespaces": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "excludedResources": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "hooks": {
                    "description": "",
                    "properties": {
                      "resources": {
                        "items": {
                          "description": "",
                          "properties": {
                            "excludedNamespaces": {
                              "description": "",
                              "items": {
                                "type": "string"
                              },
                              "nullable": true,
                              "type": "array"
                            },
                            "excludedResources": {
                              "description": "",
                              "items": {
                                "type": "string"
                              },
                              "nullable": true,
                              "type": "array"
                            },
                            "includedNamespaces": {
                              "description": "",
                              "items": {
                                "type": "string"
                              },
                              "nullable": true,
                              "type": "array"
                            },
                            "includedResources": {
                              "description": "",
                              "items": {
                                "type": "string"
                              },
                              "nullable": true,
                              "type": "array"
                            },
                            "labelSelector": {
                              "description": "",
                              "nullable": true,
                              "properties": {
                                "matchExpressions": {
                                  "description": "",
                                  "items": {
                                    "description": "",
                                    "properties": {
                                      "key": {
                                        "description": "",
                                        "type": "string"
                                      },
                                      "operator": {
                                        "description": "",
                                        "type": "string"
                                      },
                                      "values": {
                                        "description": "",
                                        "items": {
                                          "type": "string"
                                        },
                                        "type": "array"
                                      }
                                    },
                                    "required": [
                                      "key",
                                      "operator"
                                    ],
                                    "type": "object"
                                  },
                                  "type": "array"
                                },
                                "matchLabels": {
                                  "additionalProperties": {
                                    "type": "string"
                                  },
                                  "description": "",
                                  "type": "object"
                                }
                              },
                              "type": "object"
                            },
                            "name": {
                              "description": "",
                              "type": "string"
                            },
                            "postHooks": {
                              "description": "",
                              "items": {
                                "description": "",
                                "properties": {
                                  "exec": {
                                    "description": "",
                                    "properties": {
                                      "command": {
                                        "description": "",
                                        "items": {
                                          "type": "string"
                                        },
                                        "minItems": 1,
                                        "type": "array"
                                      },
                                      "container": {
                                        "description": "",
                                        "type": "string"
                                      },
                                      "execTimeout": {
                                        "description": "",
                                        "type": "string"
                                      },
                                      "onError": {
                                        "description": "",
                                        "enum": [
                                          "Continue",
                                          "Fail"
                                        ],
                                        "type": "string"
                                      },
                                      "waitTimeout": {
                                        "description": "",
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "command"
                                    ],
                                    "type": "object"
                                  },
                                  "init": {
                                    "description": "",
                                    "properties": {
                                      "initContainers": {
                                        "description": "",
                                        "items": {
                                          "description": "",
                                          "properties": {
                                            "args": {
                                              "description": "",
                                              "items": {
                                                "type": "string"
                                              },
                                              "type": "array"
                                            },
                                            "command": {
                                              "description": "",
                                              "items": {
                                                "type": "string"
                                              },
                                              "type": "array"
                                            },
                                            "env": {
                                              "description": "",
                                              "items": {
                                                "description": "",
                                                "properties": {
                                                  "name": {
                                                    "description": "",
                                                    "type": "string"
                                                  },
                                                  "value": {
                                                    "description": "",
                                                    "type": "string"
                                                  },
                                                  "valueFrom": {
                                                    "description": "",
                                                    "properties": {
                                                      "configMapKeyRef": {
                                                        "description": "",
                                                        "properties": {
                                                          "key": {
                                                            "description": "",
                                                            "type": "string"
                                                          },
                                                          "name": {
                                                            "description": "",
                                                            "type": "string"
                                                          },
                                                          "optional": {
                                                            "description": "",
                                                            "type": "boolean"
                                                          }
                                                        },
                                                        "required": [
                                                          "key"
                                                        ],
                                                        "type": "object"
                                                      },
                                                      "fieldRef": {
                                                        "description": "",
                                                        "properties": {
                                                          "apiVersion": {
                                                            "description": "",
                                                            "type": "string"
                                                          },
                                                          "fieldPath": {
                                                            "description": "",
                                                            "type": "string"
                                                          }
                                                        },
                                                        "required": [
                                                          "fieldPath"
                                                        ],
                                                        "type": "object"
                                                      },
                                                      "resourceFieldRef": {
                                                        "description": "",
                                                        "properties": {
                                                          "containerName": {
                                                            "description": "",
                                                            "type": "string"
                                                          },
                                                          "divisor": {
                                                            "anyOf": [
                                                              {
                                                                "type": "integer"
                                                              },
                                                              {
                                                                "type": "string"
                                                              }
                                                            ],
                                                            "description": "",
                                                            "pattern": "^(\\+|-)?(([0-9]+(\\.[0-9]*)?)|(\\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\\+|-)?(([0-9]+(\\.[0-9]*)?)|(\\.[0-9]+))))?$",
                                                            "x-kubernetes-int-or-string": true
                                                          },
                                                          "resource": {
                                                            "description": "",
                                                            "type": "string"
                                                          }
                                                        },
                                                        "required": [
                                                          "resource"
                                                        ],
                                                        "type": "object"
                                                      },
                                                      "secretKeyRef": {
                                                        "description": "",
                                                        "properties": {
                                                          "key": {
                                                            "description": "",
                                                            "type": "string"
                                                          },
                                                          "name": {
                                                            "description": "",
                                                            "type": "string"
                                                          },
                                                          "optional": {
                                                            "description": "",
                                                            "type": "boolean"
                                                          }
                                                        },
                                                        "required": [
                                                          "key"
                                                        ],
                                                        "type": "object"
                                                      }
                                                    },
                                                    "type": "object"
                                                  }
                                                },
                                                "required": [
                                                  "name"
                                                ],
                                                "type": "object"
                                              },
                                              "type": "array"
                                            },
                                            "envFrom": {
                                              "description": "",
                                              "items": {
                                                "description": "",
                                                "properties": {
                                                  "configMapRef": {
                                                    "description": "",
                                                    "properties": {
                                                      "name": {
                                                        "description": "",
                                                        "type": "string"
                                                      },
                                                      "optional": {
                                                        "description": "",
                                                        "type": "boolean"
                                                      }
                                                    },
                                                    "type": "object"
                                                  },
                                                  "prefix": {
                                                    "description": "",
                                                    "type": "string"
                                                  },
                                                  "secretRef": {
                                                    "description": "",
                                                    "properties": {
                                                      "name": {
                                                        "description": "",
                                                        "type": "string"
                                                      },
                                                      "optional": {
                                                        "description": "",
                                                        "type": "boolean"
                                                      }
                                                    },
                                                    "type": "object"
                                                  }
                                                },
                                                "type": "object"
                                              },
                                              "type": "array"
                                            },
                                            "image": {
                                              "description": "",
                                              "type": "string"
                                            },
                                            "imagePullPolicy": {
                                              "description": "",
                                              "type": "string"
                                            },
                                            "lifecycle": {
                                              "description": "",
                                              "properties": {
                                                "postStart": {
                                                  "description": "",
                                                  "properties": {
                                                    "exec": {
                                                      "description": "",
                                                      "properties": {
                                                        "command": {
                                                          "description": "",
                                                          "items": {
                                                            "type": "string"
                                                          },
                                                          "type": "array"
                                                        }
                                                      },
                                                      "type": "object"
                                                    },
                                                    "httpGet": {
                                                      "description": "",
                                                      "properties": {
                                                        "host": {
                                                          "description": "",
                                                          "type": "string"
                                                        },
                                                        "httpHeaders": {
                                                          "description": "",
                                                          "items": {
                                                            "description": "",
                                                            "properties": {
                                                              "name": {
                                                                "description": "",
                                                                "type": "string"
                                                              },
                                                              "value": {
                                                                "description": "",
                                                                "type": "string"
                                                              }
                                                            },
                                                            "required": [
                                                              "name",
                                                              "value"
                                                            ],
                                                            "type": "object"
                                                          },
                                                          "type": "array"
                                                        },
                                                        "path": {
                                                          "description": "",
                                                          "type": "string"
                                                        },
                                                        "port": {
                                                          "anyOf": [
                                                            {
                                                              "type": "integer"
                                                            },
                                                            {
                                                              "type": "string"
                                                            }
                                                          ],
                                                          "description": "",
                                                          "x-kubernetes-int-or-string": true
                                                        },
                                                        "scheme": {
                                                          "description": "",
                                                          "type": "string"
                                                        }
                                                      },
                                                      "required": [
                                                        "port"
                                                      ],
                                                      "type": "object"
                                                    },
                                                    "tcpSocket": {
                                                      "description": "",
                                                      "properties": {
                                                        "host": {
                                                          "description": "",
                                                          "type": "string"
                                                        },
                                                        "port": {
                                                          "anyOf": [
                                                            {
                                                              "type": "integer"
                                                            },
                                                            {
                                                              "type": "string"
                                                            }
                                                          ],
                                                          "description": "",
                                                          "x-kubernetes-int-or-string": true
                                                        }
                                                      },
                                                      "required": [
                                                        "port"
                                                      ],
                                                      "type": "object"
                                                    }
                                                  },
                                                  "type": "object"
                                                },
                                                "preStop": {
                                                  "description": "",
                                                  "properties": {
                                                    "exec": {
                                                      "description": "",
                                                      "properties": {
                                                        "command": {
                                                          "description": "",
                                                          "items": {
                                                            "type": "string"
                                                          },
                                                          "type": "array"
                                                        }
                                                      },
                                                      "type": "object"
                                                    },
                                                    "httpGet": {
                                                      "description": "",
                                                      "properties": {
                                                        "host": {
                                                          "description": "",
                                                          "type": "string"
                                                        },
                                                        "httpHeaders": {
                                                          "description": "",
                                                          "items": {
                                                            "description": "",
                                                            "properties": {
                                                              "name": {
                                                                "description": "",
                                                                "type": "string"
                                                              },
                                                              "value": {
                                                                "description": "",
                                                                "type": "string"
                                                              }
                                                            },
                                                            "required": [
                                                              "name",
                                                              "value"
                                                            ],
                                                            "type": "object"
                                                          },
                                                          "type": "array"
                                                        },
                                                        "path": {
                                                          "description": "",
                                                          "type": "string"
                                                        },
                                                        "port": {
                                                          "anyOf": [
                                                            {
                                                              "type": "integer"
                                                            },
                                                            {
                                                              "type": "string"
                                                            }
                                                          ],
                                                          "description": "",
                                                          "x-kubernetes-int-or-string": true
                                                        },
                                                        "scheme": {
                                                          "description": "",
                                                          "type": "string"
                                                        }
                                                      },
                                                      "required": [
                                                        "port"
                                                      ],
                                                      "type": "object"
                                                    },
                                                    "tcpSocket": {
                                                      "description": "",
                                                      "properties": {
                                                        "host": {
                                                          "description": "",
                                                          "type": "string"
                                                        },
                                                        "port": {
                                                          "anyOf": [
                                                            {
                                                              "type": "integer"
                                                            },
                                                            {
                                                              "type": "string"
                                                            }
                                                          ],
                                                          "description": "",
                                                          "x-kubernetes-int-or-string": true
                                                        }
                                                      },
                                                      "required": [
                                                        "port"
                                                      ],
                                                      "type": "object"
                                                    }
                                                  },
                                                  "type": "object"
                                                }
                                              },
                                              "type": "object"
                                            },
                                            "livenessProbe": {
                                              "description": "",
                                              "properties": {
                                                "exec": {
                                                  "description": "",
                                                  "properties": {
                                                    "command": {
                                                      "description": "",
                                                      "items": {
                                                        "type": "string"
                                                      },
                                                      "type": "array"
                                                    }
                                                  },
                                                  "type": "object"
                                                },
                                                "failureThreshold": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "httpGet": {
                                                  "description": "",
                                                  "properties": {
                                                    "host": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "httpHeaders": {
                                                      "description": "",
                                                      "items": {
                                                        "description": "",
                                                        "properties": {
                                                          "name": {
                                                            "description": "",
                                                            "type": "string"
                                                          },
                                                          "value": {
                                                            "description": "",
                                                            "type": "string"
                                                          }
                                                        },
                                                        "required": [
                                                          "name",
                                                          "value"
                                                        ],
                                                        "type": "object"
                                                      },
                                                      "type": "array"
                                                    },
                                                    "path": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "port": {
                                                      "anyOf": [
                                                        {
                                                          "type": "integer"
                                                        },
                                                        {
                                                          "type": "string"
                                                        }
                                                      ],
                                                      "description": "",
                                                      "x-kubernetes-int-or-string": true
                                                    },
                                                    "scheme": {
                                                      "description": "",
                                                      "type": "string"
                                                    }
                                                  },
                                                  "required": [
                                                    "port"
                                                  ],
                                                  "type": "object"
                                                },
                                                "initialDelaySeconds": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "periodSeconds": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "successThreshold": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "tcpSocket": {
                                                  "description": "",
                                                  "properties": {
                                                    "host": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "port": {
                                                      "anyOf": [
                                                        {
                                                          "type": "integer"
                                                        },
                                                        {
                                                          "type": "string"
                                                        }
                                                      ],
                                                      "description": "",
                                                      "x-kubernetes-int-or-string": true
                                                    }
                                                  },
                                                  "required": [
                                                    "port"
                                                  ],
                                                  "type": "object"
                                                },
                                                "timeoutSeconds": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                }
                                              },
                                              "type": "object"
                                            },
                                            "name": {
                                              "description": "",
                                              "type": "string"
                                            },
                                            "ports": {
                                              "description": "",
                                              "items": {
                                                "description": "",
                                                "properties": {
                                                  "containerPort": {
                                                    "description": "",
                                                    "format": "int32",
                                                    "type": "integer"
                                                  },
                                                  "hostIP": {
                                                    "description": "",
                                                    "type": "string"
                                                  },
                                                  "hostPort": {
                                                    "description": "",
                                                    "format": "int32",
                                                    "type": "integer"
                                                  },
                                                  "name": {
                                                    "description": "",
                                                    "type": "string"
                                                  },
                                                  "protocol": {
                                                    "description": "",
                                                    "type": "string"
                                                  }
                                                },
                                                "required": [
                                                  "containerPort",
                                                  "protocol"
                                                ],
                                                "type": "object"
                                              },
                                              "type": "array",
                                              "x-kubernetes-list-map-keys": [
                                                "containerPort",
                                                "protocol"
                                              ],
                                              "x-kubernetes-list-type": "map"
                                            },
                                            "readinessProbe": {
                                              "description": "",
                                              "properties": {
                                                "exec": {
                                                  "description": "",
                                                  "properties": {
                                                    "command": {
                                                      "description": "",
                                                      "items": {
                                                        "type": "string"
                                                      },
                                                      "type": "array"
                                                    }
                                                  },
                                                  "type": "object"
                                                },
                                                "failureThreshold": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "httpGet": {
                                                  "description": "",
                                                  "properties": {
                                                    "host": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "httpHeaders": {
                                                      "description": "",
                                                      "items": {
                                                        "description": "",
                                                        "properties": {
                                                          "name": {
                                                            "description": "",
                                                            "type": "string"
                                                          },
                                                          "value": {
                                                            "description": "",
                                                            "type": "string"
                                                          }
                                                        },
                                                        "required": [
                                                          "name",
                                                          "value"
                                                        ],
                                                        "type": "object"
                                                      },
                                                      "type": "array"
                                                    },
                                                    "path": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "port": {
                                                      "anyOf": [
                                                        {
                                                          "type": "integer"
                                                        },
                                                        {
                                                          "type": "string"
                                                        }
                                                      ],
                                                      "description": "",
                                                      "x-kubernetes-int-or-string": true
                                                    },
                                                    "scheme": {
                                                      "description": "",
                                                      "type": "string"
                                                    }
                                                  },
                                                  "required": [
                                                    "port"
                                                  ],
                                                  "type": "object"
                                                },
                                                "initialDelaySeconds": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "periodSeconds": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "successThreshold": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "tcpSocket": {
                                                  "description": "",
                                                  "properties": {
                                                    "host": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "port": {
                                                      "anyOf": [
                                                        {
                                                          "type": "integer"
                                                        },
                                                        {
                                                          "type": "string"
                                                        }
                                                      ],
                                                      "description": "",
                                                      "x-kubernetes-int-or-string": true
                                                    }
                                                  },
                                                  "required": [
                                                    "port"
                                                  ],
                                                  "type": "object"
                                                },
                                                "timeoutSeconds": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                }
                                              },
                                              "type": "object"
                                            },
                                            "resources": {
                                              "description": "",
                                              "properties": {
                                                "limits": {
                                                  "additionalProperties": {
                                                    "anyOf": [
                                                      {
                                                        "type": "integer"
                                                      },
                                                      {
                                                        "type": "string"
                                                      }
                                                    ],
                                                    "pattern": "^(\\+|-)?(([0-9]+(\\.[0-9]*)?)|(\\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\\+|-)?(([0-9]+(\\.[0-9]*)?)|(\\.[0-9]+))))?$",
                                                    "x-kubernetes-int-or-string": true
                                                  },
                                                  "description": "",
                                                  "type": "object"
                                                },
                                                "requests": {
                                                  "additionalProperties": {
                                                    "anyOf": [
                                                      {
                                                        "type": "integer"
                                                      },
                                                      {
                                                        "type": "string"
                                                      }
                                                    ],
                                                    "pattern": "^(\\+|-)?(([0-9]+(\\.[0-9]*)?)|(\\.[0-9]+))(([KMGTPE]i)|[numkMGTPE]|([eE](\\+|-)?(([0-9]+(\\.[0-9]*)?)|(\\.[0-9]+))))?$",
                                                    "x-kubernetes-int-or-string": true
                                                  },
                                                  "description": "",
                                                  "type": "object"
                                                }
                                              },
                                              "type": "object"
                                            },
                                            "securityContext": {
                                              "description": "",
                                              "properties": {
                                                "allowPrivilegeEscalation": {
                                                  "description": "",
                                                  "type": "boolean"
                                                },
                                                "capabilities": {
                                                  "description": "",
                                                  "properties": {
                                                    "add": {
                                                      "description": "",
                                                      "items": {
                                                        "description": "",
                                                        "type": "string"
                                                      },
                                                      "type": "array"
                                                    },
                                                    "drop": {
                                                      "description": "",
                                                      "items": {
                                                        "description": "",
                                                        "type": "string"
                                                      },
                                                      "type": "array"
                                                    }
                                                  },
                                                  "type": "object"
                                                },
                                                "privileged": {
                                                  "description": "",
                                                  "type": "boolean"
                                                },
                                                "procMount": {
                                                  "description": "",
                                                  "type": "string"
                                                },
                                                "readOnlyRootFilesystem": {
                                                  "description": "",
                                                  "type": "boolean"
                                                },
                                                "runAsGroup": {
                                                  "description": "",
                                                  "format": "int64",
                                                  "type": "integer"
                                                },
                                                "runAsNonRoot": {
                                                  "description": "",
                                                  "type": "boolean"
                                                },
                                                "runAsUser": {
                                                  "description": "",
                                                  "format": "int64",
                                                  "type": "integer"
                                                },
                                                "seLinuxOptions": {
                                                  "description": "",
                                                  "properties": {
                                                    "level": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "role": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "type": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "user": {
                                                      "description": "",
                                                      "type": "string"
                                                    }
                                                  },
                                                  "type": "object"
                                                },
                                                "windowsOptions": {
                                                  "description": "",
                                                  "properties": {
                                                    "gmsaCredentialSpec": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "gmsaCredentialSpecName": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "runAsUserName": {
                                                      "description": "",
                                                      "type": "string"
                                                    }
                                                  },
                                                  "type": "object"
                                                }
                                              },
                                              "type": "object"
                                            },
                                            "startupProbe": {
                                              "description": "",
                                              "properties": {
                                                "exec": {
                                                  "description": "",
                                                  "properties": {
                                                    "command": {
                                                      "description": "",
                                                      "items": {
                                                        "type": "string"
                                                      },
                                                      "type": "array"
                                                    }
                                                  },
                                                  "type": "object"
                                                },
                                                "failureThreshold": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "httpGet": {
                                                  "description": "",
                                                  "properties": {
                                                    "host": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "httpHeaders": {
                                                      "description": "",
                                                      "items": {
                                                        "description": "",
                                                        "properties": {
                                                          "name": {
                                                            "description": "",
                                                            "type": "string"
                                                          },
                                                          "value": {
                                                            "description": "",
                                                            "type": "string"
                                                          }
                                                        },
                                                        "required": [
                                                          "name",
                                                          "value"
                                                        ],
                                                        "type": "object"
                                                      },
                                                      "type": "array"
                                                    },
                                                    "path": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "port": {
                                                      "anyOf": [
                                                        {
                                                          "type": "integer"
                                                        },
                                                        {
                                                          "type": "string"
                                                        }
                                                      ],
                                                      "description": "",
                                                      "x-kubernetes-int-or-string": true
                                                    },
                                                    "scheme": {
                                                      "description": "",
                                                      "type": "string"
                                                    }
                                                  },
                                                  "required": [
                                                    "port"
                                                  ],
                                                  "type": "object"
                                                },
                                                "initialDelaySeconds": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "periodSeconds": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "successThreshold": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                },
                                                "tcpSocket": {
                                                  "description": "",
                                                  "properties": {
                                                    "host": {
                                                      "description": "",
                                                      "type": "string"
                                                    },
                                                    "port": {
                                                      "anyOf": [
                                                        {
                                                          "type": "integer"
                                                        },
                                                        {
                                                          "type": "string"
                                                        }
                                                      ],
                                                      "description": "",
                                                      "x-kubernetes-int-or-string": true
                                                    }
                                                  },
                                                  "required": [
                                                    "port"
                                                  ],
                                                  "type": "object"
                                                },
                                                "timeoutSeconds": {
                                                  "description": "",
                                                  "format": "int32",
                                                  "type": "integer"
                                                }
                                              },
                                              "type": "object"
                                            },
                                            "stdin": {
                                              "description": "",
                                              "type": "boolean"
                                            },
                                            "stdinOnce": {
                                              "description": "",
                                              "type": "boolean"
                                            },
                                            "terminationMessagePath": {
                                              "description": "",
                                              "type": "string"
                                            },
                                            "terminationMessagePolicy": {
                                              "description": "",
                                              "type": "string"
                                            },
                                            "tty": {
                                              "description": "",
                                              "type": "boolean"
                                            },
                                            "volumeDevices": {
                                              "description": "",
                                              "items": {
                                                "description": "",
                                                "properties": {
                                                  "devicePath": {
                                                    "description": "",
                                                    "type": "string"
                                                  },
                                                  "name": {
                                                    "description": "",
                                                    "type": "string"
                                                  }
                                                },
                                                "required": [
                                                  "devicePath",
                                                  "name"
                                                ],
                                                "type": "object"
                                              },
                                              "type": "array"
                                            },
                                            "volumeMounts": {
                                              "description": "",
                                              "items": {
                                                "description": "",
                                                "properties": {
                                                  "mountPath": {
                                                    "description": "",
                                                    "type": "string"
                                                  },
                                                  "mountPropagation": {
                                                    "description": "",
                                                    "type": "string"
                                                  },
                                                  "name": {
                                                    "description": "",
                                                    "type": "string"
                                                  },
                                                  "readOnly": {
                                                    "description": "",
                                                    "type": "boolean"
                                                  },
                                                  "subPath": {
                                                    "description": "",
                                                    "type": "string"
                                                  },
                                                  "subPathExpr": {
                                                    "description": "",
                                                    "type": "string"
                                                  }
                                                },
                                                "required": [
                                                  "mountPath",
                                                  "name"
                                                ],
                                                "type": "object"
                                              },
                                              "type": "array"
                                            },
                                            "workingDir": {
                                              "description": "",
                                              "type": "string"
                                            }
                                          },
                                          "required": [
                                            "name"
                                          ],
                                          "type": "object"
                                        },
                                        "type": "array"
                                      },
                                      "timeout": {
                                        "description": "",
                                        "type": "string"
                                      }
                                    },
                                    "type": "object"
                                  }
                                },
                                "type": "object"
                              },
                              "type": "array"
                            }
                          },
                          "required": [
                            "name"
                          ],
                          "type": "object"
                        },
                        "type": "array"
                      }
                    },
                    "type": "object"
                  },
                  "includeClusterResources": {
                    "description": "",
                    "nullable": true,
                    "type": "boolean"
                  },
                  "includedNamespaces": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "includedResources": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "labelSelector": {
                    "description": "",
                    "nullable": true,
                    "properties": {
                      "matchExpressions": {
                        "description": "",
                        "items": {
                          "description": "",
                          "properties": {
                            "key": {
                              "description": "",
                              "type": "string"
                            },
                            "operator": {
                              "description": "",
                              "type": "string"
                            },
                            "values": {
                              "description": "",
                              "items": {
                                "type": "string"
                              },
                              "type": "array"
                            }
                          },
                          "required": [
                            "key",
                            "operator"
                          ],
                          "type": "object"
                        },
                        "type": "array"
                      },
                      "matchLabels": {
                        "additionalProperties": {
                          "type": "string"
                        },
                        "description": "",
                        "type": "object"
                      }
                    },
                    "type": "object"
                  },
                  "namespaceMapping": {
                    "additionalProperties": {
                      "type": "string"
                    },
                    "description": "",
                    "type": "object"
                  },
                  "restorePVs": {
                    "description": "",
                    "nullable": true,
                    "type": "boolean"
                  },
                  "scheduleName": {
                    "description": "",
                    "type": "string"
                  }
                },
                "required": [
                  "backupName"
                ],
                "type": "object"
              },
              "status": {
                "description": "",
                "properties": {
                  "completionTimestamp": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "errors": {
                    "description": "",
                    "type": "integer"
                  },
                  "failureReason": {
                    "description": "",
                    "type": "string"
                  },
                  "phase": {
                    "description": "",
                    "enum": [
                      "New",
                      "FailedValidation",
                      "InProgress",
                      "Completed",
                      "PartiallyFailed",
                      "Failed"
                    ],
                    "type": "string"
                  },
                  "startTimestamp": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "validationErrors": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "warnings": {
                    "description": "",
                    "type": "integer"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          }
        },
        "version": "v1",
        "versions": [
          {
            "name": "v1",
            "served": true,
            "storage": true
          }
        ]
      }
    }
'''

SCHEDULE_CRD = r'''
{
      "apiVersion": "apiextensions.k8s.io/v1beta1",
      "kind": "CustomResourceDefinition",
      "metadata": {
        "annotations": {
          "controller-gen.kubebuilder.io/version": "v0.3.0"
        },
        "labels": {
          "component": "velero"
        },
        "name": "schedules.velero.io"
      },
      "spec": {
        "group": "velero.io",
        "names": {
          "kind": "Schedule",
          "listKind": "ScheduleList",
          "plural": "schedules",
          "singular": "schedule"
        },
        "preserveUnknownFields": false,
        "scope": "Namespaced",
        "validation": {
          "openAPIV3Schema": {
            "description": "",
            "properties": {
              "apiVersion": {
                "description": "",
                "type": "string"
              },
              "kind": {
                "description": "",
                "type": "string"
              },
              "metadata": {
                "type": "object"
              },
              "spec": {
                "description": "",
                "properties": {
                  "schedule": {
                    "description": "",
                    "type": "string"
                  },
                  "template": {
                    "description": "",
                    "properties": {
                      "defaultVolumesToRestic": {
                        "description": "",
                        "type": "boolean"
                      },
                      "excludedNamespaces": {
                        "description": "",
                        "items": {
                          "type": "string"
                        },
                        "nullable": true,
                        "type": "array"
                      },
                      "excludedResources": {
                        "description": "",
                        "items": {
                          "type": "string"
                        },
                        "nullable": true,
                        "type": "array"
                      },
                      "hooks": {
                        "description": "",
                        "properties": {
                          "resources": {
                            "description": "",
                            "items": {
                              "description": "",
                              "properties": {
                                "excludedNamespaces": {
                                  "description": "",
                                  "items": {
                                    "type": "string"
                                  },
                                  "nullable": true,
                                  "type": "array"
                                },
                                "excludedResources": {
                                  "description": "",
                                  "items": {
                                    "type": "string"
                                  },
                                  "nullable": true,
                                  "type": "array"
                                },
                                "includedNamespaces": {
                                  "description": "",
                                  "items": {
                                    "type": "string"
                                  },
                                  "nullable": true,
                                  "type": "array"
                                },
                                "includedResources": {
                                  "description": "",
                                  "items": {
                                    "type": "string"
                                  },
                                  "nullable": true,
                                  "type": "array"
                                },
                                "labelSelector": {
                                  "description": "",
                                  "nullable": true,
                                  "properties": {
                                    "matchExpressions": {
                                      "description": "",
                                      "items": {
                                        "description": "",
                                        "properties": {
                                          "key": {
                                            "description": "",
                                            "type": "string"
                                          },
                                          "operator": {
                                            "description": "",
                                            "type": "string"
                                          },
                                          "values": {
                                            "description": "",
                                            "items": {
                                              "type": "string"
                                            },
                                            "type": "array"
                                          }
                                        },
                                        "required": [
                                          "key",
                                          "operator"
                                        ],
                                        "type": "object"
                                      },
                                      "type": "array"
                                    },
                                    "matchLabels": {
                                      "additionalProperties": {
                                        "type": "string"
                                      },
                                      "description": "",
                                      "type": "object"
                                    }
                                  },
                                  "type": "object"
                                },
                                "name": {
                                  "description": "",
                                  "type": "string"
                                },
                                "post": {
                                  "description": "",
                                  "items": {
                                    "description": "",
                                    "properties": {
                                      "exec": {
                                        "description": "",
                                        "properties": {
                                          "command": {
                                            "description": "",
                                            "items": {
                                              "type": "string"
                                            },
                                            "minItems": 1,
                                            "type": "array"
                                          },
                                          "container": {
                                            "description": "",
                                            "type": "string"
                                          },
                                          "onError": {
                                            "description": "",
                                            "enum": [
                                              "Continue",
                                              "Fail"
                                            ],
                                            "type": "string"
                                          },
                                          "timeout": {
                                            "description": "",
                                            "type": "string"
                                          }
                                        },
                                        "required": [
                                          "command"
                                        ],
                                        "type": "object"
                                      }
                                    },
                                    "required": [
                                      "exec"
                                    ],
                                    "type": "object"
                                  },
                                  "type": "array"
                                },
                                "pre": {
                                  "description": "",
                                  "items": {
                                    "description": "",
                                    "properties": {
                                      "exec": {
                                        "description": "",
                                        "properties": {
                                          "command": {
                                            "description": "",
                                            "items": {
                                              "type": "string"
                                            },
                                            "minItems": 1,
                                            "type": "array"
                                          },
                                          "container": {
                                            "description": "",
                                            "type": "string"
                                          },
                                          "onError": {
                                            "description": "",
                                            "enum": [
                                              "Continue",
                                              "Fail"
                                            ],
                                            "type": "string"
                                          },
                                          "timeout": {
                                            "description": "",
                                            "type": "string"
                                          }
                                        },
                                        "required": [
                                          "command"
                                        ],
                                        "type": "object"
                                      }
                                    },
                                    "required": [
                                      "exec"
                                    ],
                                    "type": "object"
                                  },
                                  "type": "array"
                                }
                              },
                              "required": [
                                "name"
                              ],
                              "type": "object"
                            },
                            "nullable": true,
                            "type": "array"
                          }
                        },
                        "type": "object"
                      },
                      "includeClusterResources": {
                        "description": "",
                        "nullable": true,
                        "type": "boolean"
                      },
                      "includedNamespaces": {
                        "description": "",
                        "items": {
                          "type": "string"
                        },
                        "nullable": true,
                        "type": "array"
                      },
                      "includedResources": {
                        "description": "",
                        "items": {
                          "type": "string"
                        },
                        "nullable": true,
                        "type": "array"
                      },
                      "labelSelector": {
                        "description": "",
                        "nullable": true,
                        "properties": {
                          "matchExpressions": {
                            "description": "",
                            "items": {
                              "description": "",
                              "properties": {
                                "key": {
                                  "description": "",
                                  "type": "string"
                                },
                                "operator": {
                                  "description": "",
                                  "type": "string"
                                },
                                "values": {
                                  "description": "",
                                  "items": {
                                    "type": "string"
                                  },
                                  "type": "array"
                                }
                              },
                              "required": [
                                "key",
                                "operator"
                              ],
                              "type": "object"
                            },
                            "type": "array"
                          },
                          "matchLabels": {
                            "additionalProperties": {
                              "type": "string"
                            },
                            "description": "",
                            "type": "object"
                          }
                        },
                        "type": "object"
                      },
                      "orderedResources": {
                        "additionalProperties": {
                          "type": "string"
                        },
                        "description": "",
                        "nullable": true,
                        "type": "object"
                      },
                      "snapshotVolumes": {
                        "description": "",
                        "nullable": true,
                        "type": "boolean"
                      },
                      "storageLocation": {
                        "description": "",
                        "type": "string"
                      },
                      "ttl": {
                        "description": "",
                        "type": "string"
                      },
                      "volumeSnapshotLocations": {
                        "description": "",
                        "items": {
                          "type": "string"
                        },
                        "type": "array"
                      }
                    },
                    "type": "object"
                  }
                },
                "required": [
                  "schedule",
                  "template"
                ],
                "type": "object"
              },
              "status": {
                "description": "",
                "properties": {
                  "lastBackup": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "phase": {
                    "description": "",
                    "enum": [
                      "New",
                      "Enabled",
                      "FailedValidation"
                    ],
                    "type": "string"
                  },
                  "validationErrors": {
                    "description": "",
                    "items": {
                      "type": "string"
                    },
                    "type": "array"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          }
        },
        "version": "v1",
        "versions": [
          {
            "name": "v1",
            "served": true,
            "storage": true
          }
        ]
      }
    }
'''

SERVER_STATUS_CRD = r'''
{
      "apiVersion": "apiextensions.k8s.io/v1beta1",
      "kind": "CustomResourceDefinition",
      "metadata": {
        "annotations": {
          "controller-gen.kubebuilder.io/version": "v0.3.0"
        },
        "labels": {
          "component": "velero"
        },
        "name": "serverstatusrequests.velero.io"
      },
      "spec": {
        "group": "velero.io",
        "names": {
          "kind": "ServerStatusRequest",
          "listKind": "ServerStatusRequestList",
          "plural": "serverstatusrequests",
          "shortNames": [
            "ssr"
          ],
          "singular": "serverstatusrequest"
        },
        "preserveUnknownFields": false,
        "scope": "Namespaced",
        "subresources": {
          "status": {}
        },
        "validation": {
          "openAPIV3Schema": {
            "description": "",
            "properties": {
              "apiVersion": {
                "description": "",
                "type": "string"
              },
              "kind": {
                "description": "",
                "type": "string"
              },
              "metadata": {
                "type": "object"
              },
              "spec": {
                "description": "",
                "type": "object"
              },
              "status": {
                "description": "",
                "properties": {
                  "phase": {
                    "description": "",
                    "enum": [
                      "New",
                      "Processed"
                    ],
                    "type": "string"
                  },
                  "plugins": {
                    "description": "",
                    "items": {
                      "description": "",
                      "properties": {
                        "kind": {
                          "type": "string"
                        },
                        "name": {
                          "type": "string"
                        }
                      },
                      "required": [
                        "kind",
                        "name"
                      ],
                      "type": "object"
                    },
                    "nullable": true,
                    "type": "array"
                  },
                  "processedTimestamp": {
                    "description": "",
                    "format": "date-time",
                    "nullable": true,
                    "type": "string"
                  },
                  "serverVersion": {
                    "description": "",
                    "type": "string"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          }
        },
        "version": "v1",
        "versions": [
          {
            "name": "v1",
            "served": true,
            "storage": true
          }
        ]
      }
    }
'''

VOLUME_SNAPSHOT_CRD = r'''
{
      "apiVersion": "apiextensions.k8s.io/v1beta1",
      "kind": "CustomResourceDefinition",
      "metadata": {
        "annotations": {
          "controller-gen.kubebuilder.io/version": "v0.3.0"
        },
        "labels": {
          "component": "velero"
        },
        "name": "volumesnapshotlocations.velero.io"
      },
      "spec": {
        "group": "velero.io",
        "names": {
          "kind": "VolumeSnapshotLocation",
          "listKind": "VolumeSnapshotLocationList",
          "plural": "volumesnapshotlocations",
          "singular": "volumesnapshotlocation"
        },
        "preserveUnknownFields": false,
        "scope": "Namespaced",
        "validation": {
          "openAPIV3Schema": {
            "description": "",
            "properties": {
              "apiVersion": {
                "description": "",
                "type": "string"
              },
              "kind": {
                "description": "",
                "type": "string"
              },
              "metadata": {
                "type": "object"
              },
              "spec": {
                "description": "",
                "properties": {
                  "config": {
                    "additionalProperties": {
                      "type": "string"
                    },
                    "description": "",
                    "type": "object"
                  },
                  "provider": {
                    "description": "",
                    "type": "string"
                  }
                },
                "required": [
                  "provider"
                ],
                "type": "object"
              },
              "status": {
                "description": "",
                "properties": {
                  "phase": {
                    "description": "",
                    "enum": [
                      "Available",
                      "Unavailable"
                    ],
                    "type": "string"
                  }
                },
                "type": "object"
              }
            },
            "type": "object"
          }
        },
        "version": "v1",
        "versions": [
          {
            "name": "v1",
            "served": true,
            "storage": true
          }
        ]
      }
    }
'''

VELERO_NS = r'''
{
      "apiVersion": "v1",
      "kind": "Namespace",
      "metadata": {
        "labels": {
          "component": "velero"
        },
        "name": "velero"
      },
      "spec": {}
}
'''

VELERO_CRB = r'''
{
      "apiVersion": "rbac.authorization.k8s.io/v1beta1",
      "kind": "ClusterRoleBinding",
      "metadata": {
        "labels": {
          "component": "velero"
        },
        "name": "velero"
      },
      "roleRef": {
        "apiGroup": "rbac.authorization.k8s.io",
        "kind": "ClusterRole",
        "name": "cluster-admin"
      },
      "subjects": [
        {
          "kind": "ServiceAccount",
          "name": "velero",
          "namespace": "velero"
        }
      ]
    }
'''

VELERO_SERVICE_ACCOUNT = r'''
{
      "apiVersion": "v1",
      "kind": "ServiceAccount",
      "metadata": {
        "labels": {
          "component": "velero"
        },
        "name": "velero",
        "namespace": "velero"
      }
    }
'''

VELERO_SECRET = r'''
{
  "apiVersion":"v1",
  "kind":"Secret",
   "metadata":{
      "labels":{
         "component":"velero"
      },
      "name":"cloud-credentials",
      "namespace":"velero"
   },
  "stringData":{
      "cloud":""
    },
  "type":"Opaque"
}
'''

BACKUP_STORAGE = r'''
  {
     "apiVersion":"velero.io/v1",
     "kind":"BackupStorageLocation",
     "metadata":{
        "labels":{
           "component":"velero"
        },
        "name":"default",
        "namespace":"velero"
     },
     "spec":{
        "config":{
           "region":"",
           "s3ForcePathStyle":"true",
           "s3Url":""
        },
        "objectStorage":{
           "bucket":""
        },
        "provider":"aws"
     }
  }
'''

VELERO_DEPLOYMENT = r'''
{
      "apiVersion": "apps/v1",
      "kind": "Deployment",
      "metadata": {
        "labels": {
          "component": "velero"
        },
        "name": "velero",
        "namespace": "velero"
      },
      "spec": {
        "selector": {
          "matchLabels": {
            "deploy": "velero"
          }
        },
        "strategy": {},
        "template": {
          "metadata": {
            "annotations": {
              "prometheus.io/path": "/metrics",
              "prometheus.io/port": "8085",
              "prometheus.io/scrape": "true"
            },
            "labels": {
              "component": "velero",
              "deploy": "velero"
            }
          },
          "spec": {
            "containers": [
              {
                "args": [
                  "server",
                  "--features=EnableAPIGroupVersions",
                  "--default-volumes-to-restic=true"
                ],
                "command": [
                  "/velero"
                ],
                "env": [
                  {
                    "name": "VELERO_SCRATCH_DIR",
                    "value": "/scratch"
                  },
                  {
                    "name": "VELERO_NAMESPACE",
                    "valueFrom": {
                      "fieldRef": {
                        "fieldPath": "metadata.namespace"
                      }
                    }
                  },
                  {
                    "name": "LD_LIBRARY_PATH",
                    "value": "/plugins"
                  },
                  {
                    "name": "GOOGLE_APPLICATION_CREDENTIALS",
                    "value": "/credentials/cloud"
                  },
                  {
                    "name": "AWS_SHARED_CREDENTIALS_FILE",
                    "value": "/credentials/cloud"
                  },
                  {
                    "name": "AZURE_CREDENTIALS_FILE",
                    "value": "/credentials/cloud"
                  },
                  {
                    "name": "ALIBABA_CLOUD_CREDENTIALS_FILE",
                    "value": "/credentials/cloud"
                  }
                ],
                "image": "velero/velero:v1.6.3",
                "imagePullPolicy": "IfNotPresent",
                "name": "velero",
                "ports": [
                  {
                    "containerPort": 8085,
                    "name": "metrics"
                  }
                ],
                "resources": {
                  "limits": {
                    "cpu": "1",
                    "memory": "512Mi"
                  },
                  "requests": {
                    "cpu": "500m",
                    "memory": "128Mi"
                  }
                },
                "volumeMounts": [
                  {
                    "mountPath": "/plugins",
                    "name": "plugins"
                  },
                  {
                    "mountPath": "/scratch",
                    "name": "scratch"
                  },
                  {
                    "mountPath": "/credentials",
                    "name": "cloud-credentials"
                  }
                ]
              }
            ],
            "initContainers": [
              {
                "image": "velero/velero-plugin-for-aws:v1.1.0",
                "imagePullPolicy": "IfNotPresent",
                "name": "velero-plugin-for-aws",
                "resources": {},
                "volumeMounts": [
                  {
                    "mountPath": "/target",
                    "name": "plugins"
                  }
                ]
              }
            ],
            "restartPolicy": "Always",
            "serviceAccountName": "velero",
            "volumes": [
              {
                "emptyDir": {},
                "name": "plugins"
              },
              {
                "emptyDir": {},
                "name": "scratch"
              },
              {
                "name": "cloud-credentials",
                "secret": {
                  "secretName": "cloud-credentials"
                }
              }
            ]
          }
        }
      }
    }
'''

RESTIC_DAEMONSET = r'''
{
      "apiVersion": "apps/v1",
      "kind": "DaemonSet",
      "metadata": {
        "labels": {
          "component": "velero"
        },
        "name": "restic",
        "namespace": "velero"
      },
      "spec": {
        "selector": {
          "matchLabels": {
            "name": "restic"
          }
        },
        "template": {
          "metadata": {
            "labels": {
              "component": "velero",
              "name": "restic"
            }
          },
          "spec": {
            "containers": [
              {
                "args": [
                  "restic",
                  "server",
                  "--features="
                ],
                "command": [
                  "/velero"
                ],
                "env": [
                  {
                    "name": "NODE_NAME",
                    "valueFrom": {
                      "fieldRef": {
                        "fieldPath": "spec.nodeName"
                      }
                    }
                  },
                  {
                    "name": "VELERO_NAMESPACE",
                    "valueFrom": {
                      "fieldRef": {
                        "fieldPath": "metadata.namespace"
                      }
                    }
                  },
                  {
                    "name": "VELERO_SCRATCH_DIR",
                    "value": "/scratch"
                  },
                  {
                    "name": "GOOGLE_APPLICATION_CREDENTIALS",
                    "value": "/credentials/cloud"
                  },
                  {
                    "name": "AWS_SHARED_CREDENTIALS_FILE",
                    "value": "/credentials/cloud"
                  },
                  {
                    "name": "AZURE_CREDENTIALS_FILE",
                    "value": "/credentials/cloud"
                  },
                  {
                    "name": "ALIBABA_CLOUD_CREDENTIALS_FILE",
                    "value": "/credentials/cloud"
                  }
                ],
                "image": "velero/velero:v1.6.3",
                "imagePullPolicy": "IfNotPresent",
                "name": "restic",
                "resources": {
                  "limits": {
                    "cpu": "1",
                    "memory": "1Gi"
                  },
                  "requests": {
                    "cpu": "500m",
                    "memory": "512Mi"
                  }
                },
                "securityContext": {
                    "privileged": true
                },
                "volumeMounts": [
                  {
                    "mountPath": "/host_pods",
                    "mountPropagation": "HostToContainer",
                    "name": "host-pods"
                  },
                  {
                    "mountPath": "/scratch",
                    "name": "scratch"
                  },
                  {
                    "mountPath": "/credentials",
                    "name": "cloud-credentials"
                  }
                ]
              }
            ],
            "securityContext": {
              "runAsUser": 0
            },
            "serviceAccountName": "velero",
            "volumes": [
              {
                "hostPath": {
                  "path": "/var/lib/kubelet/pods"
                },
                "name": "host-pods"
              },
              {
                "emptyDir": {},
                "name": "scratch"
              },
              {
                "name": "cloud-credentials",
                "secret": {
                  "secretName": "cloud-credentials"
                }
              }
            ]
          }
        },
        "updateStrategy": {}
      }
    }
'''

CREATE_BACKUP_TEMPLATE = r'''
{
  "kind": "Backup",
  "apiVersion": "velero.io/v1",
  "metadata": {
    "name": "",
    "namespace": "velero"
  },
  "spec": {
    "includedNamespaces": [
      "*"
    ],
    "excludedNamespaces": [
      "velero",
      "kube-system",
      "ibm-cert-store",
      "ibm-operators",
      "ibm-system",
      "kube-node-lease",
      "kube-public",
      "ibm-observe"
    ],
    "ttl": "720h0m0s",
    "includeClusterResources": true,
    "hooks": {
    }
  },
  "status": {
  }
}
'''

CREATE_RESTORE_TEMPLATE = r'''
{
    "apiVersion": "velero.io/v1",
    "kind": "Restore",
    "metadata": {
        "generation": 3,
        "name": "",
        "namespace": "velero"
    },
    "spec": {
        "backupName": "",
        "excludedResources": [
            "CertificateSigningRequest",
            "nodes",
            "events",
            "events.events.k8s.io",
            "events.events.k8s.io/v1beta1",
            "ValidatingWebhookConfiguration.admissionregistration.k8s.io",
            "MutatingWebhookConfiguration.admissionregistration.k8s.io",
            "backups.velero.io",
            "restores.velero.io",
            "resticrepositories.velero.io",
            "crd.k8s.amazonaws.com",
            "vpcresources.k8s.aws",
            "v1beta1.events.k8s.io",
            "v1beta1.vpcresources.k8s.aws",
            "v1alpha1.crd.k8s.amazonaws.com",
            "OAuthClient.oauth.openshift.io",
            "ValidatingWebhookConfiguration.admissionregistration.k8s.io",
            "storage.k8s.io/v1",
            "StorageClass",
            "EndpointSlice"
        ],
        "hooks": {},
        "includedNamespaces": [
            "*"
        ]
    },
    "status": {
    }
}
'''

CLEANUP_CLUSTER = r'''
{
  "apiVersion": "batch/v1",
  "kind": "Job",
  "metadata": {
    "name": "velero-cleanup",
    "namespace": "velero",
    "annotations": {
      "helm.sh/hook": "pre-delete",
      "helm.sh/hook-weight": "3",
      "helm.sh/hook-delete-policy": "hook-succeeded"
    },
    "labels": {
      "app.kubernetes.io/name": "velero"
    }
  },
  "spec": {
    "template": {
      "metadata": {
        "name": "velero-cleanup"
      },
      "spec": {
        "serviceAccountName": "velero",
        "containers": [
          {
            "name": "kubectl",
            "image": "bitnami/kubectl",
            "imagePullPolicy": "IfNotPresent",
            "command": [
              "/bin/sh",
              "-c",
              "kubectl delete restore --all; kubectl delete backup --all; kubectl delete backupstoragelocation --all; kubectl delete volumesnapshotlocation --all; kubectl delete podvolumerestore --all; kubectl delete crd -l app.kubernetes.io/name=velero;\n"
            ]
          }
        ],
        "restartPolicy": "OnFailure"
      }
    }
  }
}
'''

# COS Manifests and Storage Classes


COS_DRIVER_SERVICE_ACCOUNT = r'''
{
  "apiVersion": "v1",
  "kind": "ServiceAccount",
  "metadata": {
    "name": "ibmcloud-object-storage-driver",
    "namespace": "ibm-object-s3fs",
    "annotations": {
      "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
      "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
    },
    "labels": {
      "app.kubernetes.io/name": "ibmcloud-object-storage-driver",
      "helm.sh/chart": "ibm-object-storage-plugin-2.1.4",
      "app.kubernetes.io/instance": "ibm-object-storage-plugin",
      "app.kubernetes.io/managed-by": "Helm",
      "release": "ibm-object-storage-plugin"
    }
  }
}
'''

COS_PLUGIN_SERVICE_ACCOUNT = r'''
{
  "apiVersion": "v1",
  "kind": "ServiceAccount",
  "metadata": {
    "name": "ibmcloud-object-storage-plugin",
    "namespace": "ibm-object-s3fs",
    "annotations": {
      "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
      "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
    },
    "labels": {
      "app.kubernetes.io/name": "ibmcloud-object-storage-plugin",
      "helm.sh/chart": "ibm-object-storage-plugin-2.1.4",
      "release": "ibm-object-storage-plugin",
      "app.kubernetes.io/instance": "ibm-object-storage-plugin",
      "app.kubernetes.io/managed-by": "Helm"
    }
  }
}
'''

COS_SERVICE_ACCOUNTS = [COS_DRIVER_SERVICE_ACCOUNT, COS_PLUGIN_SERVICE_ACCOUNT]

COS_PLUGIN_CLUSTER_ROLE = r'''
{
  "kind": "ClusterRole",
  "apiVersion": "rbac.authorization.k8s.io/v1",
  "metadata": {
    "name": "ibmcloud-object-storage-plugin",
    "annotations": {
      "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
      "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
    },
    "labels": {
      "app.kubernetes.io/name": "ibmcloud-object-storage-plugin",
      "helm.sh/chart": "ibm-object-storage-plugin-2.1.4",
      "release": "ibm-object-storage-plugin",
      "app.kubernetes.io/instance": "ibm-object-storage-plugin",
      "app.kubernetes.io/managed-by": "Helm"
    }
  },
  "rules": [
    {
      "apiGroups": [
        ""
      ],
      "resources": [
        "persistentvolumeclaims"
      ],
      "verbs": [
        "get",
        "list",
        "watch",
        "update"
      ]
    },
    {
      "apiGroups": [
        ""
      ],
      "resources": [
        "persistentvolumes"
      ],
      "verbs": [
        "get",
        "list",
        "watch",
        "update",
        "create",
        "delete"
      ]
    },
    {
      "apiGroups": [
        "storage.k8s.io"
      ],
      "resources": [
        "storageclasses"
      ],
      "verbs": [
        "list",
        "watch"
      ]
    },
    {
      "apiGroups": [
        ""
      ],
      "resources": [
        "events"
      ],
      "verbs": [
        "list",
        "watch",
        "create",
        "update",
        "patch"
      ]
    },
    {
      "apiGroups": [
        ""
      ],
      "resources": [
        "configmaps"
      ],
      "resourceNames": [
        "cluster-info"
      ],
      "verbs": [
        "get"
      ]
    },
    {
      "apiGroups": [
        ""
      ],
      "resources": [
        "nodes",
        "services"
      ],
      "verbs": [
        "get"
      ]
    }
  ]
}
'''

COS_PLUGIN_SECRET_READER_CLUSTER_ROLE = r'''
{
  "kind": "ClusterRole",
  "apiVersion": "rbac.authorization.k8s.io/v1",
  "metadata": {
    "name": "ibmcloud-object-storage-secret-reader",
    "annotations": {
      "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
      "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
    },
    "labels": {
      "app.kubernetes.io/name": "ibmcloud-object-storage-plugin",
      "helm.sh/chart": "ibm-object-storage-plugin-2.1.4",
      "release": "ibm-object-storage-plugin",
      "app.kubernetes.io/instance": "ibm-object-storage-plugin",
      "app.kubernetes.io/managed-by": "Helm"
    }
  },
  "rules": [
    {
      "apiGroups": [
        ""
      ],
      "resources": [
        "secrets"
      ],
      "verbs": [
        "get"
      ]
    }
  ]
}
'''

COS_CLUSTER_ROLES = [COS_PLUGIN_CLUSTER_ROLE, COS_PLUGIN_SECRET_READER_CLUSTER_ROLE]

COS_PLUGIN_CLUSTER_ROLE_BINDING = r'''
{
  "kind": "ClusterRoleBinding",
  "apiVersion": "rbac.authorization.k8s.io/v1",
  "metadata": {
    "name": "ibmcloud-object-storage-plugin",
    "annotations": {
      "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
      "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
    },
    "labels": {
      "app.kubernetes.io/name": "ibmcloud-object-storage-plugin",
      "helm.sh/chart": "ibm-object-storage-plugin-2.1.4",
      "release": "ibm-object-storage-plugin",
      "app.kubernetes.io/instance": "ibm-object-storage-plugin",
      "app.kubernetes.io/managed-by": "Helm"
    }
  },
  "subjects": [
    {
      "kind": "ServiceAccount",
      "name": "ibmcloud-object-storage-plugin",
      "namespace": "ibm-object-s3fs"
    }
  ],
  "roleRef": {
    "kind": "ClusterRole",
    "name": "ibmcloud-object-storage-plugin",
    "apiGroup": "rbac.authorization.k8s.io"
  }
}
'''

COS_PLUGIN_SECRET_READER_CLUSTER_ROLE_BINDING = r'''
{
  "kind": "ClusterRoleBinding",
  "apiVersion": "rbac.authorization.k8s.io/v1",
  "metadata": {
    "name": "ibmcloud-object-storage-secret-reader",
    "annotations": {
      "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
      "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
    },
    "labels": {
      "app.kubernetes.io/name": "ibmcloud-object-storage-plugin",
      "helm.sh/chart": "ibm-object-storage-plugin-2.1.4",
      "release": "ibm-object-storage-plugin",
      "app.kubernetes.io/instance": "ibm-object-storage-plugin",
      "app.kubernetes.io/managed-by": "Helm"
    }
  },
  "subjects": [
    {
      "kind": "ServiceAccount",
      "name": "ibmcloud-object-storage-plugin",
      "namespace": "ibm-object-s3fs"
    }
  ],
  "roleRef": {
    "kind": "ClusterRole",
    "name": "ibmcloud-object-storage-secret-reader",
    "apiGroup": "rbac.authorization.k8s.io"
  }
}
'''

COS_CLUSTER_ROLE_BINDING = [COS_PLUGIN_CLUSTER_ROLE_BINDING, COS_PLUGIN_SECRET_READER_CLUSTER_ROLE_BINDING]

COS_DRIVER_DAEMONSET = r'''
{
  "apiVersion": "apps/v1",
  "kind": "DaemonSet",
  "metadata": {
    "name": "ibmcloud-object-storage-driver",
    "namespace": "ibm-object-s3fs",
    "annotations": {
      "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
      "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
    },
    "labels": {
      "app": "ibmcloud-object-storage-driver",
      "app.kubernetes.io/name": "ibmcloud-object-storage-driver",
      "helm.sh/chart": "ibm-object-storage-plugin-2.1.4",
      "app.kubernetes.io/instance": "ibm-object-storage-plugin",
      "app.kubernetes.io/managed-by": "Helm",
      "release": "ibm-object-storage-plugin"
    }
  },
  "spec": {
    "updateStrategy": {
      "rollingUpdate": {
        "maxUnavailable": 1
      },
      "type": "RollingUpdate"
    },
    "selector": {
      "matchLabels": {
        "app": "ibmcloud-object-storage-driver"
      }
    },
    "template": {
      "metadata": {
        "labels": {
          "app": "ibmcloud-object-storage-driver",
          "app.kubernetes.io/name": "ibmcloud-object-storage-driver",
          "helm.sh/chart": "ibm-object-storage-plugin-2.1.4",
          "app.kubernetes.io/instance": "ibm-object-storage-plugin",
          "app.kubernetes.io/managed-by": "Helm",
          "release": "ibm-object-storage-plugin"
        },
        "annotations": {
          "productID": "IBMCloudObjectStoragePlugin_2.1.4_Apache02_00000",
          "productMetric": "FREE",
          "productName": "ibmcloud-object-storage-plugin",
          "productVersion": "2.1.4",
          "autoUpdate": "V0bNE",
          "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
          "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
        }
      },
      "spec": {
        "affinity": {
          "nodeAffinity": {
            "requiredDuringSchedulingIgnoredDuringExecution": {
              "nodeSelectorTerms": [
                {
                  "matchExpressions": [
                    {
                      "key": "kubernetes.io/arch",
                      "operator": "In",
                      "values": [
                        "amd64"
                      ]
                    }
                  ]
                }
              ]
            }
          }
        },
        "tolerations": [
          {
            "operator": "Exists"
          }
        ],
        "hostNetwork": true,
        "hostPID": false,
        "hostIPC": false,
        "serviceAccountName": "ibmcloud-object-storage-driver",
        "containers": [
          {
            "name": "ibmcloud-object-storage-driver-container",
            "image": "icr.io/ibm/ibmcloud-object-storage-driver@sha256:e9152b9e7dfca10cf02f8de7a8d14a4067e7fe69695699411cadaf282263f099",
            "imagePullPolicy": "Always",
            "resources": {
              "requests": {
                "memory": "128Mi",
                "cpu": "200m"
              },
              "limits": {
                "memory": "128Mi",
                "cpu": "200m"
              }
            },
            "securityContext": {
              "capabilities": {
                "drop": [
                  "ALL"
                ]
              },
              "privileged": false,
              "allowPrivilegeEscalation": true,
              "readOnlyRootFilesystem": true,
              "runAsNonRoot": false,
              "runAsUser": 0
            },
            "livenessProbe": {
              "exec": {
                "command": [
                  "sh",
                  "-c",
                  "version1=$(cat /home/s3-dep/version.txt | grep \"^Version\" ); version2=$(/host/kubernetes/kubelet-plugins/volume/exec/ibm~ibmc-s3fs/ibmc-s3fs version); if [ \"$version1\" = \"$version2\" ]; then exit 0; else exit 1; fi"
                ]
              },
              "initialDelaySeconds": 60,
              "timeoutSeconds": 5,
              "periodSeconds": 60,
              "failureThreshold": 1
            },
            "readinessProbe": {
              "exec": {
                "command": [
                  "sh",
                  "-c",
                  "version1=$(cat /home/s3-dep/version.txt | grep \"^Version\" ); version2=$(/host/kubernetes/kubelet-plugins/volume/exec/ibm~ibmc-s3fs/ibmc-s3fs version); if [ \"$version1\" == \"$version2\" ]; then exit 0; else exit 1; fi"
                ]
              },
              "initialDelaySeconds": 60,
              "timeoutSeconds": 5,
              "periodSeconds": 60,
              "failureThreshold": 1
            },
            "volumeMounts": [
              {
                "mountPath": "/host/kubernetes",
                "name": "kube-driver"
              },
              {
                "mountPath": "/host/local",
                "name": "usr-local"
              },
              {
                "mountPath": "/host/usr/lib",
                "name": "usr-lib",
                "readOnly": true
              },
              {
                "mountPath": "/host/etc",
                "name": "etc-mount"
              },
              {
                "mountPath": "/host/log",
                "name": "host-logs",
                "readOnly": true
              }
            ]
          }
        ],
        "volumes": [
          {
            "name": "kube-driver",
            "hostPath": {
              "path": "/usr/libexec/kubernetes"
            }
          },
          {
            "name": "usr-local",
            "hostPath": {
              "path": "/usr/local"
            }
          },
          {
            "name": "usr-lib",
            "hostPath": {
              "path": "/usr/lib"
            }
          },
          {
            "name": "etc-mount",
            "hostPath": {
              "path": "/etc"
            }
          },
          {
            "name": "host-logs",
            "hostPath": {
              "path": "/var/log"
            }
          }
        ]
      }
    }
  }
}
'''

COS_PLUGIN_DEPLOYMENT = r'''
{
  "apiVersion": "apps/v1",
  "kind": "Deployment",
  "metadata": {
    "name": "ibmcloud-object-storage-plugin",
    "namespace": "ibm-object-s3fs",
    "annotations": {
      "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
      "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
    },
    "labels": {
      "app": "ibmcloud-object-storage-plugin",
      "helm.sh/chart": "ibm-object-storage-plugin-2.1.4",
      "release": "ibm-object-storage-plugin",
      "app.kubernetes.io/managed-by": "Helm",
      "app.kubernetes.io/instance": "ibm-object-storage-plugin",
      "app.kubernetes.io/name": "ibmcloud-object-storage-plugin"
    }
  },
  "spec": {
    "strategy": {
      "type": "RollingUpdate"
    },
    "replicas": 1,
    "selector": {
      "matchLabels": {
        "app": "ibmcloud-object-storage-plugin"
      }
    },
    "template": {
      "metadata": {
        "labels": {
          "app": "ibmcloud-object-storage-plugin",
          "app.kubernetes.io/name": "ibmcloud-object-storage-plugin",
          "helm.sh/chart": "ibm-object-storage-plugin-2.1.4",
          "release": "ibm-object-storage-plugin",
          "app.kubernetes.io/instance": "ibm-object-storage-plugin",
          "app.kubernetes.io/managed-by": "Helm"
        },
        "annotations": {
          "productID": "IBMCloudObjectStoragePlugin_2.1.4_Apache02_00000",
          "productMetric": "FREE",
          "productName": "ibmcloud-object-storage-plugin",
          "productVersion": "2.1.4",
          "autoUpdate": "k0uar",
          "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
          "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
        }
      },
      "spec": {
        "affinity": {
          "nodeAffinity": {
            "requiredDuringSchedulingIgnoredDuringExecution": {
              "nodeSelectorTerms": [
                {
                  "matchExpressions": [
                    {
                      "key": "kubernetes.io/arch",
                      "operator": "In",
                      "values": [
                        "amd64"
                      ]
                    }
                  ]
                }
              ]
            }
          }
        },
        "tolerations": [
          {
            "operator": "Exists"
          }
        ],
        "hostNetwork": false,
        "hostPID": false,
        "hostIPC": false,
        "serviceAccountName": "ibmcloud-object-storage-plugin",
        "containers": [
          {
            "name": "ibmcloud-object-storage-plugin-container",
            "image": "icr.io/ibm/ibmcloud-object-storage-plugin@sha256:b2e7a3ced38cb9197e7d1a3bea3ffcc9dda46e7d12ca5337e5ba8d4253659309",
            "imagePullPolicy": "Always",
            "resources": {
              "requests": {
                "memory": "128Mi",
                "cpu": "200m"
              },
              "limits": {
                "memory": "128Mi",
                "cpu": "200m"
              }
            },
            "securityContext": {
              "capabilities": {
                "drop": [
                  "ALL"
                ]
              },
              "privileged": false,
              "allowPrivilegeEscalation": false,
              "readOnlyRootFilesystem": true,
              "runAsNonRoot": true
            },
            "livenessProbe": {
              "exec": {
                "command": [
                  "sh",
                  "-c",
                  "ps aux | grep \"provisioner=ibm.io/ibmc-s3fs\" | grep -v grep > /dev/null"
                ]
              },
              "initialDelaySeconds": 30,
              "timeoutSeconds": 5,
              "periodSeconds": 65,
              "failureThreshold": 1
            },
            "readinessProbe": {
              "exec": {
                "command": [
                  "sh",
                  "-c",
                  "ps aux | grep \"provisioner=ibm.io/ibmc-s3fs\" | grep -v grep > /dev/null"
                ]
              },
              "initialDelaySeconds": 30,
              "timeoutSeconds": 5,
              "periodSeconds": 60,
              "failureThreshold": 1
            },
            "args": [
              "-provisioner=ibm.io/ibmc-s3fs",
              "--endpoint=$(ENDPOINT)",
              "--bucketAccessPolicy=$(CONFIG_BUCKET_ACCESS_POLICY)"
            ],
            "env": [
              {
                "name": "DEBUG_TRACE",
                "value": "false"
              },
              {
                "name": "ENDPOINT",
                "value": "/ibmprovider/provider.sock"
              },
              {
                "name": "CONFIG_BUCKET_ACCESS_POLICY",
                "value": "false"
              }
            ],
            "volumeMounts": [
              {
                "mountPath": "/ibmprovider",
                "name": "socket-dir"
              }
            ]
          }
        ],
        "volumes": [
          {
            "emptyDir": {},
            "name": "socket-dir"
          },
          {
            "name": "customer-auth",
            "secret": {
              "secretName": "storage-secret-store"
            }
          },
          {
            "name": "cluster-info",
            "configMap": {
              "name": "cluster-info"
            }
          }
        ]
      }
    }
  }
}
'''

COS_STORAGE_DRIVER_POD = r'''
{
  "apiVersion": "v1",
  "kind": "Pod",
  "metadata": {
    "name": "ibmcloud-object-storage-driver",
    "namespace": "ibm-object-s3fs",
    "labels": {
      "release": "ibm-object-storage-plugin",
      "app.kubernetes.io/name": "ibmcloud-object-storage-driver",
      "helm.sh/chart": "ibm-object-storage-plugin-2.1.4",
      "app.kubernetes.io/instance": "ibm-object-storage-plugin",
      "app.kubernetes.io/managed-by": "Helm"
    },
    "annotations": {
      "helm.sh/hook": "success",
      "helm.sh/hook-delete-policy": "hook-succeeded"
    }
  },
  "spec": {
    "affinity": {
      "nodeAffinity": {
        "requiredDuringSchedulingIgnoredDuringExecution": {
          "nodeSelectorTerms": [
            {
              "matchExpressions": [
                {
                  "key": "kubernetes.io/arch",
                  "operator": "In",
                  "values": [
                    "amd64"
                  ]
                }
              ]
            }
          ]
        }
      }
    },
    "tolerations": [
      {
        "operator": "Exists"
      }
    ],
    "hostNetwork": true,
    "hostPID": false,
    "hostIPC": false,
    "serviceAccountName": "ibmcloud-object-storage-driver",
    "containers": [
      {
        "name": "ibmcloud-object-storage-driver",
        "image": "icr.io/ibm/ibmcloud-object-storage-driver@sha256:e9152b9e7dfca10cf02f8de7a8d14a4067e7fe69695699411cadaf282263f099",
        "imagePullPolicy": "Always",
        "command": [
          "sh",
          "-c",
          "ls /host/kubernetes/kubelet-plugins/volume/exec/ibm~ibmc-s3fs/ibmc-s3fs; rc=$?; exit $rc"
        ],
        "resources": {
          "requests": {
            "memory": "128Mi",
            "cpu": "200m"
          },
          "limits": {
            "memory": "128Mi",
            "cpu": "200m"
          }
        },
        "securityContext": {
          "capabilities": {
            "drop": [
              "ALL"
            ]
          },
          "privileged": false,
          "allowPrivilegeEscalation": true,
          "readOnlyRootFilesystem": true,
          "runAsNonRoot": false,
          "runAsUser": 0
        },
        "volumeMounts": [
          {
            "mountPath": "/host/kubernetes",
            "name": "kube-driver"
          }
        ]
      }
    ],
    "restartPolicy": "Never",
    "volumes": [
      {
        "name": "kube-driver",
        "hostPath": {
          "path": "/usr/libexec/kubernetes"
        }
      }
    ]
  }
}
'''

COS_STORAGE_CLASS_COLD_CROSS_REGION = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-cold-cross-region",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "16",
      "ibm.io/parallel-count": "2",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "false",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "NA",
      "ibm.io/object-store-storage-class": "NA"
   }
}
'''

COS_STORAGE_CLASS_COLD_REGIONAL = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-cold-regional",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "16",
      "ibm.io/parallel-count": "2",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "false",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "https://s3.direct.REGION.cloud-object-storage.appdomain.cloud",
      "ibm.io/object-store-storage-class": "jp-tok-cold"
   }
}
'''

COS_STORAGE_CLASS_FLEX_CROSS_REGION = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-flex-cross-region",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "16",
      "ibm.io/parallel-count": "2",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "true",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "NA",
      "ibm.io/object-store-storage-class": "NA"
   }
}
'''

COS_STORAGE_CLASS_FLEX_PERF_CROSS_REGION = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-flex-perf-cross-region",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "52",
      "ibm.io/parallel-count": "20",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "true",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "NA",
      "ibm.io/object-store-storage-class": "NA"
   }
}
'''

COS_STORAGE_CLASS_FLEX_PERF_REGIONAL = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-flex-perf-regional",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "52",
      "ibm.io/parallel-count": "20",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "true",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "https://s3.direct.REGION.cloud-object-storage.appdomain.cloud",
      "ibm.io/object-store-storage-class": "jp-tok-smart"
   }
}
'''

COS_STORAGE_CLASS_FLEX_REGIONAL = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-flex-regional",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "16",
      "ibm.io/parallel-count": "2",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "true",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "https://s3.direct.REGION.cloud-object-storage.appdomain.cloud",
      "ibm.io/object-store-storage-class": "jp-tok-smart"
   }
}
'''

COS_STORAGE_CLASS_STANDARD_CROSS_REGION = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-standard-cross-region",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "16",
      "ibm.io/parallel-count": "2",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "true",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "NA",
      "ibm.io/object-store-storage-class": "NA"
   }
}
'''

COS_STORAGE_CLASS_STANDARD_PERF_CROSS_REGION = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-standard-perf-cross-region",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "52",
      "ibm.io/parallel-count": "20",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "true",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "NA",
      "ibm.io/object-store-storage-class": "NA"
   }
}
'''

COS_STORAGE_CLASS_STANDARD_PERF_REGIONAL = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-standard-perf-regional",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "52",
      "ibm.io/parallel-count": "20",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "true",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "https://s3.direct.REGION.cloud-object-storage.appdomain.cloud",
      "ibm.io/object-store-storage-class": "jp-tok-standard"
   }
}
'''

COS_STORAGE_CLASS_STANDARD_REGIONAL = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-standard-regional",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "16",
      "ibm.io/parallel-count": "2",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "true",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "https://s3.direct.REGION.cloud-object-storage.appdomain.cloud",
      "ibm.io/object-store-storage-class": "jp-tok-standard"
   }
}
'''

COS_STORAGE_CLASS_VAULT_CROSS_REGION = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-vault-cross-region",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "16",
      "ibm.io/parallel-count": "2",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "false",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "NA",
      "ibm.io/object-store-storage-class": "NA"
   }
}
'''

COS_STORAGE_CLASS_VAULT_REGIONAL = r'''
{
   "kind": "StorageClass",
   "apiVersion": "storage.k8s.io/v1",
   "metadata": {
      "name": "ibmc-s3fs-vault-regional",
      "annotations": {
         "razee.io/source-url": "https://github.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/commit/b7b9932768dc26a844ec874b85a99b57955bc116",
         "razee.io/build-url": "https://travis.ibm.com/alchemy-containers/armada-storage-s3fs-plugin/builds/42287521"
      },
      "labels": {
         "app": "ibmcloud-object-storage-plugin",
         "chart": "ibm-object-storage-plugin-2.1.4",
         "release": "ibm-object-storage-plugin",
         "heritage": "Helm"
      }
   },
   "provisioner": "ibm.io/ibmc-s3fs",
   "parameters": {
      "ibm.io/chunk-size-mb": "16",
      "ibm.io/parallel-count": "2",
      "ibm.io/multireq-max": "20",
      "ibm.io/tls-cipher-suite": "AESGCM",
      "ibm.io/stat-cache-size": "100000",
      "ibm.io/debug-level": "warn",
      "ibm.io/curl-debug": "false",
      "ibm.io/kernel-cache": "false",
      "ibm.io/s3fs-fuse-retry-count": "5",
      "ibm.io/iam-endpoint": "https://private.iam.cloud.ibm.com",
      "ibm.io/object-store-endpoint": "https://s3.direct.REGION.cloud-object-storage.appdomain.cloud",
      "ibm.io/object-store-storage-class": "jp-tok-vault"
   }
}
'''

COS_STORAGE_CLASSES = [COS_STORAGE_CLASS_COLD_CROSS_REGION, COS_STORAGE_CLASS_COLD_REGIONAL,
                       COS_STORAGE_CLASS_FLEX_CROSS_REGION, COS_STORAGE_CLASS_FLEX_PERF_CROSS_REGION,
                       COS_STORAGE_CLASS_FLEX_PERF_REGIONAL, COS_STORAGE_CLASS_FLEX_REGIONAL,
                       COS_STORAGE_CLASS_STANDARD_CROSS_REGION, COS_STORAGE_CLASS_STANDARD_PERF_CROSS_REGION,
                       COS_STORAGE_CLASS_STANDARD_PERF_REGIONAL, COS_STORAGE_CLASS_STANDARD_REGIONAL,
                       COS_STORAGE_CLASS_VAULT_CROSS_REGION, COS_STORAGE_CLASS_VAULT_REGIONAL]

# PVC Templates

COS_PVC = r'''
{
  "kind": "PersistentVolumeClaim",
  "apiVersion": "v1",
  "metadata": {
    "name": "",
    "namespace": "",
    "annotations": {
      "ibm.io/auto-create-bucket": "true",
      "ibm.io/auto-delete-bucket": "false",
      "ibm.io/bucket": "",
      "ibm.io/secret-name": "cos-write-access"
    }
  },
  "spec": {
    "accessModes": [
      ""
    ],
    "resources": {
      "requests": {
        "storage": ""
      }
    },
    "storageClassName": "ibmc-s3fs-standard-regional"
  }
}
'''

BLOCK_STORAGE_PVC = r'''
{
  "kind": "PersistentVolumeClaim",
  "apiVersion": "v1",
  "metadata": {
    "name": "",
    "namespace": ""
  },
  "spec": {
    "accessModes": [
      ""
    ],
    "resources": {
      "requests": {
        "storage": ""
      }
    },
    "storageClassName": ""
  }
}
'''
