// SPDX-License-Identifier: GPL-3.0-or-later
using UnrealBuildTool;
public class SilkroadLandscapeBridge : ModuleRules {
 public SilkroadLandscapeBridge(ReadOnlyTargetRules Target) : base(Target) {
  PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs;
  PublicDependencyModuleNames.AddRange(new string[]{"Core","CoreUObject","Engine","Landscape"});
  PrivateDependencyModuleNames.AddRange(new string[]{"UnrealEd","Json","AssetRegistry"});
 }
}
