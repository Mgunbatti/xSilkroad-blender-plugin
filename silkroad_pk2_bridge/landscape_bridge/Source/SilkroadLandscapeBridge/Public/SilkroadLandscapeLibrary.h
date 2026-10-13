// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "SilkroadLandscapeLibrary.generated.h"
class ALandscape;
class UMaterialInterface;
UCLASS()
class SILKROADLANDSCAPEBRIDGE_API USilkroadLandscapeLibrary : public UBlueprintFunctionLibrary {
 GENERATED_BODY()
public:
 UFUNCTION(BlueprintCallable, Category="Silkroad|Jangan")
 static ALandscape* ImportManifest(const FString& ManifestPath, UMaterialInterface* Material, const FString& AssetRoot, FString& Error);
 UFUNCTION(BlueprintCallable, Category="Silkroad|Jangan")
 static FString ValidateLandscape(ALandscape* Landscape, const FString& ManifestPath);
 UFUNCTION(BlueprintCallable, Category="Silkroad|Jangan")
 static void FinalizeImport(ALandscape* Landscape);
};
