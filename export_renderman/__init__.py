
#Blender 2.5 or later to Renderman Exporter
#Author: Sascha Fricke



#############################################################################################
#                                                                                           #
#       Begin GPL Block                                                                     #
#                                                                                           #
#############################################################################################
#                                                                                           #
#This program is free software;                                                             #
#you can redistribute it and/or modify it under the terms of the                            #
#GNU General Public License as published by the Free Software Foundation;                   #
#either version 3 of the LicensGe, or (at your option) any later version.                   #
#                                                                                           #
#This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;  #
#without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  #
#See the GNU General Public License for more details.                                       #
#                                                                                           #
#You should have received a copy of the GNU General Public License along with this program; #
#if not, see <http://www.gnu.org/licenses/>.                                                #
#                                                                                           #
#############################################################################################
#                                                                                           #
#       End GPL Block                                                                       #
#                                                                                           #
############################################################################################

#Thanks to: Campbell Barton, Eric Back, Nathan Vegdahl

##################################################################################################################################


bl_info = {
    'name': 'Renderman',
    'author': 'Sascha Fricke',
    'version': '0.01',
    'blender': (2, 5, 6),
    'location': 'Info Header',
    'description': 'Connects Blender to Renderman Interface',
    'category': 'Render'}
    
##################################################################################################################################
if "bpy" in locals():
    reload(rm_props)
    reload(ops)
    reload(maintain)
    reload(ui)
    reload(export)
else:
    import export_renderman
    import export_renderman.ops
    from export_renderman.ops import *
    import export_renderman.rm_maintain
    from export_renderman.rm_maintain import *
    import export_renderman.ui
    from export_renderman.ui import *
    import export_renderman.export
    from export_renderman.export import *

import bpy
import properties_render
import os
import subprocess
import math
import mathutils
import tempfile
import time

##################################################################################################################################

import properties_data_mesh
import properties_data_camera
import properties_data_lamp
import properties_texture
import properties_particle

#properties_render.RENDER_PT_render.COMPAT_ENGINES.add('RENDERMAN')
#properties_render.RENDER_PT_dimensions.COMPAT_ENGINES.add('RENDERMAN')
#properties_render.RENDER_PT_output.COMPAT_ENGINES.add('RENDERMAN')
#properties_render.RENDER_PT_post_processing.COMPAT_ENGINES.add('RENDERMAN')
properties_data_mesh.DATA_PT_context_mesh.COMPAT_ENGINES.add('RENDERMAN')
properties_data_mesh.DATA_PT_settings.COMPAT_ENGINES.add('RENDERMAN')
properties_data_mesh.DATA_PT_vertex_groups.COMPAT_ENGINES.add('RENDERMAN')
properties_data_mesh.DATA_PT_shape_keys.COMPAT_ENGINES.add('RENDERMAN')
properties_data_mesh.DATA_PT_uv_texture.COMPAT_ENGINES.add('RENDERMAN')
properties_data_camera.DATA_PT_context_camera.COMPAT_ENGINES.add('RENDERMAN')
properties_data_camera.DATA_PT_camera_display.COMPAT_ENGINES.add('RENDERMAN')
properties_data_lamp.DATA_PT_context_lamp.COMPAT_ENGINES.add('RENDERMAN')

for member in dir(properties_texture):
    subclass = getattr(properties_texture, member)
    exceptions = [  "", "Colors", "Influence", "Mapping", 
                    "Image Sampling", "Image Mapping", 
                    "Environment Map Sampling", "Custom Properties",
                    "Preview", "Environment Map"]
    try:
        if not subclass.bl_label in exceptions:
            subclass.COMPAT_ENGINES.add('RENDERMAN')
    except:
        pass

for member in dir(properties_particle):
    subclass = getattr(properties_particle, member)
    exceptions = ['Render', 'Children']
    try:
        if not subclass.bl_label in exceptions:
            subclass.COMPAT_ENGINES.add('RENDERMAN')
    except:
        pass
            
del properties_texture
del properties_data_mesh
del properties_data_camera
del properties_data_lamp

exported_instances = []

##################################################################################################################################
#checking folders and creating them if necessary

def checkpaths(folderpath):
    if os.path.exists(folderpath):
        fullofcrap = True
        dir = folderpath
        while fullofcrap:
            if not os.path.exists(dir):
                fullofcrap = False
                break
            if os.listdir(dir):
                for item in os.listdir(dir):
                    if os.path.isfile(os.path.join(dir, item)):
                        os.remove(os.path.join(dir, item))
                    elif os.path.isdir(os.path.join(dir, item)):
                        dir = os.path.join(folderpath, item)
            else:
                os.rmdir(dir)
                dir = folderpath
    os.mkdir(folderpath)


##################################################################################################################################
##################################################################################################################################

##################################################################################################################################

##################################################################################################################################


#########################################################################################################
#                                                                                                       #
#       R E N D E R                                                                                     #
#                                                                                                       #
#########################################################################################################
preview_scene = False

def checksize(img):
    size = -1

    ready = False
    while not ready:
        if size != os.path.getsize(img):
            size = os.path.getsize(img)
        else:
            ready = True
            break

        time.sleep(1)
    return 0

class Renderman_OT_Render(bpy.types.Operator):
    bl_label = "Render"
    bl_idname = "renderman.render"
    bl_description = "Export/Render Scene using Renderman"
    
    anim = bpy.props.BoolProperty(default = False)
    
    def invoke(self, context, event):
        scene = context.scene
        path = getdefaultribpath(scene)        
        checkpaths(path)
        checkpaths(os.path.join(path, scene.renderman_settings.texdir))
        if self.anim:
            for i in range(context.frame_start, scene.frame_end+scene.frame_step, scene.frame_step):
                scene.frame_set(i)
                render(scene)
        else:
            render(scene)
        return{'FINISHED'}   

def image(name, scene): return name.replace("[frame]", framepadding(scene))

def start_render(render, ribfile, current_pass, scene):
    r = scene.render
    x = int(r.resolution_x * r.resolution_percentage * 0.01)
    y = int(r.resolution_y * r.resolution_percentage * 0.01)

#    if current_pass.displaydrivers and not current_pass.shadow:
#        print("Render .. "+current_pass.name)
#        print(render + ' ' + ribfile)
        
        #renderprocess = subprocess.Popen([render, ribfile])                                         
#        while not renderprocess.poll:
#            if rhandle.test_break():
#                try:
#                    renderprocess.terminate()
#                except:
#                    renderprocess.kill()
#    else:
    renderprocess = subprocess.Popen([render, ribfile])      
                 
    #wait for the file to be completely written
    for disp in current_pass.displaydrivers:
        if not disp.displaydriver == "framebuffer":
            img = image(disp.file, scene)
            while not os.path.exists(img): ###wait for the file to be created
                pass            
            checksize(img)

            
    ## until the render api is fixed, load all images manually in the image editor
    for disp in current_pass.displaydrivers:
        if not disp.displaydriver == "framebuffer" or current_pass.shadow or current_pass.environment:
            img = image(disp.file, scene)
            if not img in bpy.data.images and not disp.displaydriver == "framebuffer":
                bpy.data.images.load(img) 
       
def render(scene):
    rndr = scene.renderman_settings.renderexec
    rm = scene.renderman_settings
    rs = rm.rib_structure    
    if rndr != "":
        maintain(eval("bpy.context"))
        path = getdefaultribpath(scene)
                                             
        active_pass = getactivepass(scene)

        global exported_instances
        pname = getname(rs.frame.filename,
                        scene=scene,
                        frame=framepadding(scene))+'.rib'
        
        filepath = os.path.join(path, pname)
                
        if scene.renderman_settings.exportallpasses:
            global base_archive
            base_archive = Archive(data_path=scene, type="Frame", scene=scene, filepath=filepath)
            for item in scene.renderman_settings.passes:
                imagefolder = os.path.join(getdefaultribpath(scene), item.imagedir)
                checkForPath(imagefolder)                                       

                exported_instances = []

                export(item, scene)
            close_all()
            if not scene.renderman_settings.exportonly:
                if rndr != "" and not item.environment:
                    start_render(rndr, base_archive.filepath, item, scene)
                    check_disps_processing(item, scene)
        else:

            exported_instances = []


            export(active_pass, scene)
            close_all()
            imagefolder = os.path.join(path, active_pass.imagedir)
            checkpaths(imagefolder)
            if not scene.renderman_settings.exportonly:
               if rndr != "":
                   start_render(rndr, base_archive.filepath, active_pass, scene)
                   check_disps_processing(active_pass, scene)
       
update_counter = 0
class RendermanRender(bpy.types.RenderEngine):
    bl_idname = 'RENDERMAN'
    bl_label = "Renderman"
    bl_use_preview = True
    update = 50
    
    def rm_start_render(self, render, ribfile, current_pass, scene):
        rc = current_pass.renderman_camera
        x = int(rc.resx * rc.respercentage)*0.01
        y = int(rc.resy * rc.respercentage)*0.01
        
        self.update_stats("", "Render ... "+current_pass.name)
    
        if current_pass.displaydrivers:
            print("Render .. "+current_pass.name)
            print(render + ' ' + ribfile)
            
            renderprocess = subprocess.Popen([render, ribfile])
           
            def image(name): return name.replace("[frame]", framepadding(scene))    

            def update_image(image):
                result = self.begin_result(0, 0, x, y)
              
                layer = result.layers[0]
                
                try:
                    layer.load_from_file(image)
                except:
                    print("can't load image")
                self.end_result(result)

            if (current_pass.renderresult != ""
                and current_pass.displaydrivers[current_pass.renderresult].displaydriver != "framebuffer"):
                img = image(current_pass.displaydrivers[current_pass.renderresult].file)
                
                while not os.path.exists(img):
                    if os.path.exists(img):
                        break                 
                   
                    if self.test_break():
                        try:
                            renderprocess.terminate()
                        except:
                            renderprocess.kill()
            
                    if renderprocess.poll() == 0:
                        self.update_stats("", "Error: Check Console")
                        break            
                                      
                prev_size = -1
                ready = False
               
                dbprint("all image files created, now load them", lvl=2, grp="renderprocess")
                dbprint("renderprocess finished?", renderprocess.poll(), lvl=2, grp="renderprocess")
                while True:
                    dbprint("Rendering ...", lvl=2, grp="renderprocess")
                    update_image(img)
#                            if renderprocess.poll():
#                                print("Finished")
#                                self.update_stats("", "Finished")
#                                update_image(layname, image)
#                                break
    
                    if self.test_break():
                        dbprint("aborting rendering", lvl=2, grp="renderprocess")
                        try:
                            renderprocess.terminate()
                        except:
                            renderprocess.kill()
                        break
              
                    if renderprocess.poll() == 0:
                        dbprint("renderprocess terminated", lvl=2, grp="renderprocess")
                        break
              
                    if os.path.getsize(img) != prev_size:
                        prev_size = os.path.getsize(img) 
                        update_image(img)                                                               
                            
            ## until the render api is fixed, load all images manually in the image editor
            try:
                for disp in current_pass.displaydrivers:
                    img = image(disp.file)
                    if not disp.displaydriver == "framebuffer":
                        if not img in bpy.data.images:
                            bpy.data.images.load(image(img))
                        else: bpy.data.images[img].update()
            except SystemError:
                pass

    def render(self, scene):
        rm = scene.renderman_settings
        rs = rm.rib_structure
        if scene.name == "preview":
            global update_counter
            update_counter += 1
            if update_counter < self.update:
                return
            update_counter = 0
            mat, rndr = preview_mat()
            matrm = mat.renderman[mat.renderman_index]

            rmprdir = bpy.utils.preset_paths("renderman")[0]
            mat_preview_path = os.path.join(rmprdir, "material_previews")
            if matrm.preview_scene == "":
                return
            previewdir = os.path.join(mat_preview_path, matrm.preview_scene)
            previewdir_materialdir = os.path.join(previewdir, "Materials")
            mat_archive_file = os.path.join(previewdir_materialdir, "preview_material.rib")
            mat_archive = Archive(data_path=mat, filepath=mat_archive_file, scene=scene)
            print(mat.name)
            writeMaterial(mat, mat_archive=mat_archive, active_matpass=True)
            ribfile = os.path.join(previewdir, "material_preview.rib")
            renderprocess = subprocess.Popen([rndr, ribfile])  

            def update_image(image):
                result = self.begin_result(0, 0, 128, 128)
              
                layer = result.layers[0]
                try:
                    layer.load_from_file(image)
                    loaded = True
                except SystemError:
                    loaded = False
                self.end_result(result)
                return loaded

            img = os.path.join(previewdir, "material_preview.tiff")
            
            while not os.path.exists(img):
                if os.path.exists(img):
                    break                 
        
                if renderprocess.poll() == 0:
                    break            

            while not renderprocess.poll() == 0:
                update_image(img)
            update_image(img)

            
        else:        
            rndr = scene.renderman_settings.renderexec
            if rndr == "":
                return
            
            path = getdefaultribpath(scene)
            pname = getname(rs.frame.filename,
                            scene=scene,
                            frame=framepadding(scene))+'.rib'
            
            filepath = os.path.join(path, pname)
                    
            rndr = scene.renderman_settings.renderexec

                                                 
            active_pass = getactivepass(scene)
    
            global exported_instances, base_archive
            base_archive = Archive(data_path=scene, type="Frame", scene=scene, filepath=filepath)
    
            if scene.renderman_settings.exportallpasses:
                for item in scene.renderman_settings.passes:
                    imagefolder = os.path.join(getdefaultribpath(scene), item.imagedir)
                    checkForPath(imagefolder)                                       
    
                    exported_instances = []
    
                    export(item, scene)
                close_all()
                if not scene.renderman_settings.exportonly:
                    if rndr != "":
                        self.rm_start_render(rndr, base_archive.filepath, item, scene)
                        check_disps_processing(item, scene)
            else:
                exported_instances = []
    
    
                export(active_pass, scene)
                close_all()
                imagefolder = os.path.join(path, active_pass.imagedir)
                checkpaths(imagefolder)
                if not scene.renderman_settings.exportonly:
                   if rndr != "":
                       self.rm_start_render(rndr, base_archive.filepath, active_pass, scene)
                       check_disps_processing(active_pass, scene)

##################################################################################################################################

##################################################################################################################################

##################################################################################################################################
##################################################################################################################################




##################################################################################################################################

def register():
    import export_renderman.rm_props
    bpy.types.VIEW3D_MT_object_specials.append(draw_obj_specials_rm_menu)
    
    

def unregister():
    bpy.types.VIEW3D_MT_object_specials.remove(draw_obj_specials_rm_menu)

if __name__ == "__main__":
    register()
