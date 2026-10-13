// SPDX-License-Identifier: GPL-3.0-or-later
#include "SilkroadLandscapeLibrary.h"
#include "Modules/ModuleManager.h"
#include "Landscape.h"
#include "LandscapeInfo.h"
#include "LandscapeComponent.h"
#include "EngineUtils.h"
#include "LandscapeLayerInfoObject.h"
#include "Materials/MaterialInterface.h"
#include "Editor.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "AssetRegistry/AssetRegistryModule.h"
IMPLEMENT_MODULE(FDefaultModuleImpl, SilkroadLandscapeBridge)

ALandscape* USilkroadLandscapeLibrary::ImportManifest(const FString& ManifestPath, UMaterialInterface* Material, const FString& AssetRoot, FString& Error) {
 Error.Empty();auto Fail=[&](const FString& Text)->ALandscape*{Error=Text;return nullptr;};
 FString Text;TSharedPtr<FJsonObject> M;
 if(!FFileHelper::LoadFileToString(Text,*ManifestPath)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),M)||!M.IsValid())return Fail(TEXT("Invalid Landscape manifest"));
 FString Format,Scope;
 if(!M->TryGetStringField(TEXT("format"),Format)||Format!=TEXT("silkroad-jangan-landscape-1")||!M->TryGetStringField(TEXT("scope"),Scope)||Scope!=TEXT("Jangan"))return Fail(TEXT("Jangan Landscape exports only"));
 const TSet<int32> Allowed={22942,22943,23196,23197,23198,23199,23200,23201,23202,23203,23204,23452,23453,23454,23455,23456,23457,23458,23459,23460,23461,23462,23463,23464,23465,23466,23467,23468,23708,23709,23710,23711,23712,23713,23714,23715,23716,23717,23718,23719,23720,23721,23722,23723,23724,23725,23964,23965,23966,23967,23968,23969,23970,23971,23972,23973,23974,23975,23976,23977,23978,23979,23980,23981,24220,24221,24222,24223,24224,24225,24226,24227,24228,24229,24230,24231,24232,24233,24234,24235,24236,24237,24477,24478,24479,24480,24481,24482,24483,24484,24485,24486,24487,24488,24489,24490,24491,24492,24493,24733,24734,24735,24736,24737,24738,24739,24740,24741,24742,24743,24744,24745,24746,24747,24748,24749,24990,24991,24992,24993,24994,24995,24996,24997,24998,24999,25000,25001,25002,25003,25004,25005,25250,25251,25252,25253,25254,25255,25256,25257,25258,25259,25260,25261,25507,25508,25509,25510,25511,25512,25513,25514,25515,25516,25517,25765,25766,25767,25768,25769,25770,25771,25772,25773,25774,26021,26022,26023,26024,26025,26027,26028,26029,26284};
 const TArray<TSharedPtr<FJsonValue>>* Regions;
 if(!M->TryGetArrayField(TEXT("regions"),Regions)||Regions->IsEmpty())return Fail(TEXT("Missing Jangan regions"));
 for(auto& R:*Regions)if(!Allowed.Contains((int32)R->AsNumber()))return Fail(TEXT("Region outside Jangan scope"));
 const int32 W=M->GetIntegerField(TEXT("width")),H=M->GetIntegerField(TEXT("height")),Q=M->GetIntegerField(TEXT("subsection_quads"));
 if(W<2||H<2||W>2048||H>2048||Q!=63||(W-1)%Q||(H-1)%Q||!Material)return Fail(TEXT("Invalid Landscape dimensions or material"));
 const int32 Count=W*H;const FString Dir=FPaths::GetPath(ManifestPath);
 auto Read=[&](const FString& File,TArray<uint8>& Bytes,int32 Expected){return !File.Contains(TEXT(".."))&&FPaths::IsRelative(File)&&FFileHelper::LoadFileToArray(Bytes,*(Dir/File))&&Bytes.Num()==Expected;};
 TArray<uint8> Raw;if(!Read(M->GetStringField(TEXT("height_file")),Raw,Count*2))return Fail(TEXT("Height.r16 missing or invalid size"));
 TArray<uint16> Height;Height.SetNumUninitialized(Count);for(int32 I=0;I<Count;++I)Height[I]=Raw[I*2]|(Raw[I*2+1]<<8);
 const auto& Layers=M->GetArrayField(TEXT("layers"));TArray<FLandscapeImportLayerInfo> Infos;
 for(auto& L:Layers){
  const auto& O=L->AsObject();FString Name=O->GetStringField(TEXT("name"));
  if(Name!=TEXT("Soil")&&Name!=TEXT("Grass")&&Name!=TEXT("DryGrass")&&Name!=TEXT("WetSoil")&&Name!=TEXT("Paving")&&Name!=TEXT("Rock")&&Name!=TEXT("Visibility"))return Fail(TEXT("Unsupported paint layer"));
  FLandscapeImportLayerInfo Info{FName(*Name)};
  if(!Read(O->GetStringField(TEXT("file")),Info.LayerData,Count))return Fail(TEXT("Layer file missing or invalid size: ")+Name);
  Info.SourceFilePath=Dir/O->GetStringField(TEXT("file"));
  if(Name==TEXT("Visibility")){Info.LayerInfo=ALandscapeProxy::VisibilityLayer;Info.LayerName=Info.LayerInfo->GetLayerName();}
  else{
   FString Path=AssetRoot+TEXT("/Layers/LI_")+Name;UPackage* Package=CreatePackage(*Path);
   auto* LI=FindObject<ULandscapeLayerInfoObject>(Package,*(TEXT("LI_")+Name));
   if(!LI){LI=NewObject<ULandscapeLayerInfoObject>(Package,*(TEXT("LI_")+Name),RF_Public|RF_Standalone);LI->SetLayerName(FName(*Name),false);FAssetRegistryModule::AssetCreated(LI);}
   LI->SetBlendMethod(ELandscapeTargetLayerBlendMethod::FinalWeightBlending,false);LI->MarkPackageDirty();Info.LayerInfo=LI;
  }
  Infos.Add(MoveTemp(Info));
 }
 const auto& Origin=M->GetArrayField(TEXT("origin_cm"));const auto& Scale=M->GetArrayField(TEXT("scale"));
 if(Origin.Num()!=3||Scale.Num()!=3)return Fail(TEXT("Invalid Landscape transform"));
 FVector P(Origin[0]->AsNumber(),Origin[1]->AsNumber(),Origin[2]->AsNumber()),S(Scale[0]->AsNumber(),Scale[1]->AsNumber(),Scale[2]->AsNumber());
 if(P.ContainsNaN()||S.ContainsNaN()||S.X!=200||S.Y!=200||S.Z<=0)return Fail(TEXT("Invalid Landscape scale"));
 UWorld* World=GEditor?GEditor->GetEditorWorldContext().World():nullptr;if(!World)return Fail(TEXT("An editor level must be open"));
 FActorSpawnParameters Params;Params.ObjectFlags=RF_Transactional;
 auto* Landscape=World->SpawnActor<ALandscape>(ALandscape::StaticClass(),P,FRotator::ZeroRotator,Params);
 if(!Landscape)return Fail(TEXT("Landscape spawn failed"));Landscape->SetActorScale3D(S);Landscape->LandscapeMaterial=Material;Landscape->SetActorLabel(TEXT("Silkroad_Jangan_Landscape"));
 for(const auto& I:Infos)Landscape->AddTargetLayer(I.LayerName,FLandscapeTargetLayerSettings(I.LayerInfo,I.SourceFilePath),false);
 TMap<FGuid,TArray<uint16>> Heights;Heights.Add(FGuid(),MoveTemp(Height));TMap<FGuid,TArray<FLandscapeImportLayerInfo>> Paint;Paint.Add(FGuid(),MoveTemp(Infos));
 TArray<FLandscapeLayer> EditLayers;
 Landscape->Import(FGuid::NewGuid(),0,0,W-1,H-1,1,Q,Heights,*(Dir/M->GetStringField(TEXT("height_file"))),Paint,ELandscapeImportAlphamapType::Additive,EditLayers);
 Landscape->RegisterAllComponents();Landscape->GetLandscapeInfo()->UpdateLayerInfoMap(Landscape);Landscape->UpdateAllComponentMaterialInstances();Landscape->RequestLayersContentUpdateForceAll();Landscape->MarkPackageDirty();
 FinalizeImport(Landscape);return Landscape;
}

void USilkroadLandscapeLibrary::FinalizeImport(ALandscape* Landscape){
 if(!Landscape)return;Landscape->LandscapeHoleMaterial=Landscape->LandscapeMaterial;Landscape->UpdateAllComponentMaterialInstances();
 TInlineComponentArray<ULandscapeComponent*> Components;Landscape->GetComponents(Components);
 for(auto* C:Components)C->UpdateCollisionLayerData();
 Landscape->RecreateCollisionComponents();Landscape->MarkPackageDirty();
}

FString USilkroadLandscapeLibrary::ValidateLandscape(ALandscape* Landscape,const FString& ManifestPath){
 if(!Landscape)return TEXT("{}");FString Text;TSharedPtr<FJsonObject> M;
 if(!FFileHelper::LoadFileToString(Text,*ManifestPath)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),M))return TEXT("{}");
 TArray<uint8> Raw;FFileHelper::LoadFileToArray(Raw,*(FPaths::GetPath(ManifestPath)/M->GetStringField(TEXT("height_file"))));int32 W=M->GetIntegerField(TEXT("width"));
 TSharedRef<FJsonObject> R=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Samples,Allocations;FCollisionQueryParams Params;
 for(TActorIterator<AActor> It(Landscape->GetWorld());It;++It)if(*It!=Landscape)Params.AddIgnoredActor(*It);
 double MaxError=0;bool AllHit=true;
  TArray<uint8> Visibility;FFileHelper::LoadFileToArray(Visibility,*(FPaths::GetPath(ManifestPath)/TEXT("Visibility.r8")));
 int32 SW=M->GetIntegerField(TEXT("source_width")),SH=M->GetIntegerField(TEXT("source_height"));TArray<FIntPoint> Points;
 for(int32 Y=12;Y<SH-12;Y+=FMath::Max(16,(SH-24)/7))for(int32 X=12;X<SW-12;X+=FMath::Max(16,(SW-24)/9))if(Visibility.IsValidIndex(Y*W+X)&&Visibility[Y*W+X]==0)Points.Add({X,Y});
 for(FIntPoint P:Points){
  int32 I=2*(P.Y*W+P.X);if(I+1>=Raw.Num())continue;double Expected=((Raw[I]|(Raw[I+1]<<8))-32768)*Landscape->GetActorScale3D().Z/128+Landscape->GetActorLocation().Z;
  FVector V=Landscape->GetActorLocation()+FVector(P.X*200,P.Y*200,0);V.Z=Expected;FHitResult Hit;bool Found=Landscape->GetWorld()->LineTraceSingleByChannel(Hit,V+FVector(0,0,5000),V-FVector(0,0,5000),ECC_Pawn,Params);
  double E=Found?FMath::Abs(Hit.ImpactPoint.Z-Expected):1e9;MaxError=FMath::Max(E,MaxError);AllHit&=Found;TSharedRef<FJsonObject> S=MakeShared<FJsonObject>();S->SetBoolField(TEXT("hit"),Found);S->SetNumberField(TEXT("error_cm"),E);Samples.Add(MakeShared<FJsonValueObject>(S));
 }
 FHitResult Pad;FVector V=Landscape->GetActorLocation()+FVector((SW+(W-SW)/2)*200,(SH+(M->GetIntegerField(TEXT("height"))-SH)/2)*200,0);bool PadHit=Landscape->GetWorld()->LineTraceSingleByChannel(Pad,V+FVector(0,0,40000),V-FVector(0,0,40000),ECC_Pawn,Params);
 TInlineComponentArray<ULandscapeComponent*> Components;Landscape->GetComponents(Components);for(auto* C:Components)for(const auto& A:C->GetWeightmapLayerAllocations())if(A.LayerInfo)Allocations.Add(MakeShared<FJsonValueString>(A.LayerInfo->GetLayerName().ToString()));
 R->SetArrayField(TEXT("traces"),Samples);R->SetArrayField(TEXT("allocated_layers"),Allocations);R->SetNumberField(TEXT("max_collision_error_cm"),MaxError);R->SetBoolField(TEXT("all_hit"),AllHit);R->SetBoolField(TEXT("padding_collision_removed"),!PadHit);R->SetNumberField(TEXT("edit_layers"),Landscape->GetEditLayers().Num());
 FString Out;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Out));return Out;
}
