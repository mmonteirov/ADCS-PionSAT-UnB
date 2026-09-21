cmake_minimum_required(VERSION 3.16)

if(NOT DEFINED ENV{IDF_PATH} AND DEFINED IDF_PATH)
    set(ENV{IDF_PATH} "${IDF_PATH}")
endif()

set(COMPONENTS main)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(pion_sat_adcs)
